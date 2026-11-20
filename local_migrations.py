from datetime import datetime
import os
import re
import sqlite3

from werkzeug.security import generate_password_hash


def _column_names(cursor, table_name):
    return {row[1] for row in cursor.execute(f'PRAGMA table_info({table_name})').fetchall()}


def _table_exists(cursor, table_name):
    result = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return result is not None


def _slugify(value):
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or 'tenant-local'


def _ensure_column(cursor, table_name, column_name, definition):
    columns = _column_names(cursor, table_name)
    if column_name not in columns:
        cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}')


def _ensure_v5_etapas_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS etapa (
            id INTEGER NOT NULL PRIMARY KEY,
            tarefa_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            titulo VARCHAR(200) NOT NULL,
            descricao TEXT,
            ordem INTEGER NOT NULL,
            data_planejada DATE,
            hora_inicio TIME,
            hora_fim TIME,
            status VARCHAR(20) NOT NULL DEFAULT 'Criada',
            concluida_em DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_etapa_tarefa_ordem UNIQUE (tarefa_id, ordem),
            CONSTRAINT ck_etapa_status CHECK (status IN ('Criada', 'Iniciada', 'Pausada', 'Concluida')),
            FOREIGN KEY(tarefa_id) REFERENCES tarefa (id),
            FOREIGN KEY(tenant_id) REFERENCES tenant (id),
            FOREIGN KEY(user_id) REFERENCES user (id)
        )
        """
    )
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_etapa_tarefa_id ON etapa (tarefa_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_etapa_tenant_id ON etapa (tenant_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_etapa_user_id ON etapa (user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_etapa_status ON etapa (status)')

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_etapa (
            id INTEGER NOT NULL PRIMARY KEY,
            tarefa_id INTEGER NOT NULL,
            etapa_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            acao VARCHAR(50) NOT NULL,
            descricao TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_historico_etapa_acao CHECK (
                acao IN ('criar', 'editar', 'iniciar', 'pausar', 'retomar', 'concluir', 'excluir', 'reordenar')
            ),
            FOREIGN KEY(tarefa_id) REFERENCES tarefa (id),
            FOREIGN KEY(etapa_id) REFERENCES etapa (id),
            FOREIGN KEY(tenant_id) REFERENCES tenant (id),
            FOREIGN KEY(user_id) REFERENCES user (id)
        )
        """
    )
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_historico_etapa_tarefa_id ON historico_etapa (tarefa_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_historico_etapa_etapa_id ON historico_etapa (etapa_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_historico_etapa_tenant_id ON historico_etapa (tenant_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_historico_etapa_user_id ON historico_etapa (user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_historico_etapa_acao ON historico_etapa (acao)')


def _hora_inicio_obrigatoria(cursor):
    for coluna in cursor.execute('PRAGMA table_info(tarefa)').fetchall():
        if coluna[1] == 'hora_inicio':
            return bool(coluna[3])
    return False


def _contar_problemas_fk(cursor):
    return len(cursor.execute('PRAGMA foreign_key_check').fetchall())


def _tornar_hora_inicio_opcional(con):
    """Reconstroi a tabela tarefa sem o NOT NULL de hora_inicio (SQLite nao altera restricao).

    Parte do DDL gravado no proprio banco, porque os bancos antigos tem DDL diferentes.
    Idempotente: nao faz nada se hora_inicio ja aceita vazio.
    """
    cur = con.cursor()
    if not _table_exists(cur, 'tarefa') or not _hora_inicio_obrigatoria(cur):
        return

    ddl = cur.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'tarefa'").fetchone()[0]
    novo_ddl, trocas = re.subn(r'(\bhora_inicio\s+TIME)\s+NOT\s+NULL', r'\1', ddl, count=1, flags=re.IGNORECASE)
    if trocas != 1:
        raise RuntimeError('Migracao data_inicio: hora_inicio NOT NULL nao encontrado no DDL da tabela tarefa.')
    novo_ddl, trocas = re.subn(
        r'^\s*CREATE\s+TABLE\s+["`\[]?tarefa["`\]]?', 'CREATE TABLE tarefa__nova', novo_ddl, count=1, flags=re.IGNORECASE
    )
    if trocas != 1:
        raise RuntimeError('Migracao data_inicio: cabecalho CREATE TABLE tarefa nao reconhecido.')

    colunas = ', '.join(f'"{coluna[1]}"' for coluna in cur.execute('PRAGMA table_info(tarefa)').fetchall())
    indices = [
        linha[0] for linha in cur.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'tarefa' AND sql IS NOT NULL"
        ).fetchall()
    ]

    con.commit()
    cur.execute('PRAGMA foreign_keys=OFF')
    try:
        problemas_antes = _contar_problemas_fk(cur)
        total_antes = cur.execute('SELECT COUNT(*) FROM tarefa').fetchone()[0]
        cur.execute('BEGIN')
        cur.execute(novo_ddl)
        cur.execute(f'INSERT INTO tarefa__nova ({colunas}) SELECT {colunas} FROM tarefa')
        cur.execute('DROP TABLE tarefa')
        cur.execute('ALTER TABLE tarefa__nova RENAME TO tarefa')
        for sql in indices:
            cur.execute(sql)

        total_depois = cur.execute('SELECT COUNT(*) FROM tarefa').fetchone()[0]
        if total_depois != total_antes:
            raise RuntimeError(f'Migracao data_inicio: {total_antes} tarefas antes e {total_depois} depois.')
        if _contar_problemas_fk(cur) > problemas_antes:
            raise RuntimeError('Migracao data_inicio: a reconstrucao gerou chaves estrangeiras invalidas.')
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        cur.execute('PRAGMA foreign_keys=ON')


def run_local_migrations(db_path):
    """Executa migracoes locais idempotentes para o MVP SQLite."""
    if not os.path.exists(db_path):
        return

    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tenant (
                id INTEGER NOT NULL PRIMARY KEY,
                nome VARCHAR(120) NOT NULL,
                slug VARCHAR(120) NOT NULL UNIQUE,
                created_at DATETIME
            )
            """
        )
        cur.execute('CREATE INDEX IF NOT EXISTS ix_tenant_slug ON tenant (slug)')

        if _table_exists(cur, 'user'):
            _ensure_column(cur, 'user', 'tenant_id', 'INTEGER')
            _ensure_column(cur, 'user', 'failed_login_attempts', 'INTEGER NOT NULL DEFAULT 0')
            _ensure_column(cur, 'user', 'locked_until', 'DATETIME')
            _ensure_column(cur, 'user', 'created_at', 'DATETIME')
            cur.execute('CREATE INDEX IF NOT EXISTS ix_user_tenant_id ON user (tenant_id)')

        if _table_exists(cur, 'categoria'):
            _ensure_column(cur, 'categoria', 'tenant_id', 'INTEGER')
            cur.execute('CREATE INDEX IF NOT EXISTS ix_categoria_tenant_id ON categoria (tenant_id)')

        if _table_exists(cur, 'tarefa'):
            _ensure_column(cur, 'tarefa', 'tenant_id', 'INTEGER')
            cur.execute('CREATE INDEX IF NOT EXISTS ix_tarefa_tenant_id ON tarefa (tenant_id)')
            # V5.1: data de inicio escolhida pelo usuario (opcional).
            _ensure_column(cur, 'tarefa', 'data_inicio', 'DATE')

        users = cur.execute('SELECT id, username, password, tenant_id FROM user').fetchall() if _table_exists(cur, 'user') else []
        now = datetime.utcnow().isoformat(sep=' ', timespec='seconds')

        if users:
            for user_id, username, password, tenant_id in users:
                if tenant_id is None:
                    slug_base = _slugify(username)
                    slug = slug_base
                    suffix = 2
                    while cur.execute('SELECT 1 FROM tenant WHERE slug = ?', (slug,)).fetchone():
                        slug = f'{slug_base}-{suffix}'
                        suffix += 1

                    cur.execute(
                        'INSERT INTO tenant (nome, slug, created_at) VALUES (?, ?, ?)',
                        (f'Tenant {username}', slug, now),
                    )
                    tenant_id = cur.lastrowid
                    cur.execute('UPDATE user SET tenant_id = ?, created_at = COALESCE(created_at, ?) WHERE id = ?', (tenant_id, now, user_id))

                if password and not password.startswith(('scrypt:', 'pbkdf2:', 'argon2:', 'bcrypt:')):
                    cur.execute(
                        'UPDATE user SET password = ? WHERE id = ?',
                        (generate_password_hash(password), user_id),
                    )

            cur.execute(
                """
                UPDATE categoria
                   SET tenant_id = (
                       SELECT tenant_id FROM user WHERE user.id = categoria.user_id
                   )
                 WHERE tenant_id IS NULL
                """
            )
            cur.execute(
                """
                UPDATE tarefa
                   SET tenant_id = (
                       SELECT tenant_id FROM user WHERE user.id = tarefa.user_id
                   )
                WHERE tenant_id IS NULL
                """
            )

        if _table_exists(cur, 'tarefa') and _table_exists(cur, 'tenant') and _table_exists(cur, 'user'):
            _ensure_v5_etapas_tables(cur)

        con.commit()

        # V5.1: a hora de inicio pertence a data de inicio e passa a ser opcional.
        _tornar_hora_inicio_opcional(con)
    finally:
        con.close()
