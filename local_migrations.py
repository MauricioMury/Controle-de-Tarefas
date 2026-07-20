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

        con.commit()
    finally:
        con.close()
