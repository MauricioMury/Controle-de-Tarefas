from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Tenant(db.Model):
    """Tenant do sistema multi-tenant."""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    usuarios = db.relationship('User', backref='tenant', lazy=True)
    tarefas = db.relationship('Tarefa', backref='tenant', lazy=True)
    categorias = db.relationship('Categoria', backref='tenant', lazy=True)
    etapas = db.relationship('Etapa', backref='tenant', lazy=True)
    historicos_etapa = db.relationship('HistoricoEtapa', backref='tenant', lazy=True)

    def __repr__(self):
        return f'<Tenant {self.slug}>'


class User(UserMixin, db.Model):
    """Modelo de usuario do sistema."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False, index=True)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    email_notif = db.Column(db.String(120), nullable=True)
    whatsapp_numero = db.Column(db.String(30), nullable=True)
    whatsapp_apikey = db.Column(db.String(100), nullable=True)

    tarefas = db.relationship('Tarefa', backref='usuario', lazy=True, cascade='all, delete-orphan')
    categorias = db.relationship('Categoria', backref='usuario', lazy=True, cascade='all, delete-orphan')
    etapas = db.relationship('Etapa', backref='usuario', lazy=True, cascade='all, delete-orphan')
    historicos_etapa = db.relationship('HistoricoEtapa', backref='usuario', lazy=True, cascade='all, delete-orphan')


class Categoria(db.Model):
    """Modelo de categorias customizadas por usuario."""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    cor = db.Column(db.String(20), default='info')
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Categoria {self.nome}>'


class Tarefa(db.Model):
    """Modelo de tarefas do usuario."""
    id = db.Column(db.Integer, primary_key=True)
    tarefa = db.Column(db.String(200), nullable=False)
    comentario = db.Column(db.Text, nullable=True)
    # Cada hora pertence a sua data: hora_inicio -> data_inicio, hora_fim -> data_realizado.
    # A data meta nao tem hora. Horas antigas sem a data correspondente ficam gravadas, mas nao sao exibidas.
    data_inicio = db.Column(db.Date, nullable=True)
    data_meta = db.Column(db.Date, nullable=False)
    data_realizado = db.Column(db.Date, nullable=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fim = db.Column(db.Time, nullable=True)
    prioridade = db.Column(db.String(20), nullable=False)
    recorrencia = db.Column(db.String(50), nullable=False)
    categoria_legado = db.Column('categoria', db.String(50), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='Pendente')
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    categoria = db.relationship('Categoria', backref=db.backref('tarefas', lazy=True))
    etapas = db.relationship(
        'Etapa',
        backref='tarefa_ref',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='Etapa.ordem',
    )
    historicos_etapa = db.relationship('HistoricoEtapa', backref='tarefa_ref', lazy=True)

    notif_datetime_1 = db.Column(db.DateTime, nullable=True)
    notif_email_enviada_1 = db.Column(db.Boolean, default=False, nullable=False)
    notif_whatsapp_enviada_1 = db.Column(db.Boolean, default=False, nullable=False)

    notif_datetime_2 = db.Column(db.DateTime, nullable=True)
    notif_email_enviada_2 = db.Column(db.Boolean, default=False, nullable=False)
    notif_whatsapp_enviada_2 = db.Column(db.Boolean, default=False, nullable=False)

    def dias_atraso(self, hoje=None):
        """Dias de atraso em relacao a meta (0 se no prazo).

        Concluida: data realizado - meta. Pendente: hoje - meta (exige `hoje`).
        """
        if self.data_realizado:
            referencia = self.data_realizado
        elif hoje is not None:
            referencia = hoje
        else:
            return 0
        return max(0, (referencia - self.data_meta).days)

    def get_prioridade_cor(self):
        cores = {
            'Muito Importante': 'danger',
            'Importante': 'warning',
            'Normal': 'primary',
        }
        return cores.get(self.prioridade, 'secondary')

    def get_dia_semana_ordem(self):
        dias = {
            'SEGUNDA': 1,
            'TERCA': 2,
            'QUARTA': 3,
            'QUINTA': 4,
            'SEXTA': 5,
            'SABADO': 6,
            'DOMINGO': 7,
        }
        mapa_dias = {
            'MONDAY': 'SEGUNDA',
            'TUESDAY': 'TERCA',
            'WEDNESDAY': 'QUARTA',
            'THURSDAY': 'QUINTA',
            'FRIDAY': 'SEXTA',
            'SATURDAY': 'SABADO',
            'SUNDAY': 'DOMINGO',
        }
        dia_nome = self.data_meta.strftime('%A').upper()
        dia_pt = mapa_dias.get(dia_nome, 'SEGUNDA')
        return dias.get(dia_pt, 1)

    def __repr__(self):
        return f'<Tarefa {self.tarefa}>'


class Etapa(db.Model):
    """Etapa de execucao vinculada a uma tarefa."""
    __table_args__ = (
        db.UniqueConstraint('tarefa_id', 'ordem', name='uq_etapa_tarefa_ordem'),
        db.CheckConstraint(
            "status IN ('Criada', 'Iniciada', 'Pausada', 'Concluida')",
            name='ck_etapa_status',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefa.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ordem = db.Column(db.Integer, nullable=False)
    data_planejada = db.Column(db.Date, nullable=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fim = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Criada')
    concluida_em = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    historicos = db.relationship(
        'HistoricoEtapa',
        backref='etapa_ref',
        lazy=True,
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<Etapa {self.titulo}>'


class HistoricoEtapa(db.Model):
    """Historico de acoes realizadas em uma etapa."""
    __table_args__ = (
        db.CheckConstraint(
            "acao IN ('criar', 'editar', 'iniciar', 'pausar', 'retomar', 'concluir', 'excluir', 'reordenar')",
            name='ck_historico_etapa_acao',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tarefa_id = db.Column(db.Integer, db.ForeignKey('tarefa.id'), nullable=False, index=True)
    etapa_id = db.Column(db.Integer, db.ForeignKey('etapa.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    acao = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<HistoricoEtapa {self.acao}>'
