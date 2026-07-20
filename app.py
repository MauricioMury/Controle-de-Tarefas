import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

from local_migrations import run_local_migrations
from models import Categoria, User, db
from routes import register_auth_routes, register_routes


load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


@event.listens_for(Engine, 'connect')
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if dbapi_connection.__class__.__module__.startswith('sqlite3'):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


app = Flask(__name__)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY deve ser definida no arquivo .env ou no ambiente.')

APP_ENV = os.environ.get('APP_ENV', 'Producao')
DATABASE_FILENAME = 'tarefas-desenvolvimento.db' if APP_ENV == 'Desenvolvimento' else 'tarefas.db'

app.config['SECRET_KEY'] = SECRET_KEY
app.config['APP_ENV'] = APP_ENV
app.config['DATABASE_FILENAME'] = DATABASE_FILENAME
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_FILENAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar esta página.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.after_request
def security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    return response


@app.context_processor
def inject_mvp_context():
    return {
        'local_username': current_user.username if current_user.is_authenticated else '',
        'current_user': current_user,
        'notifications_enabled': False,
    }


def criar_categorias_padrao(usuario):
    categorias_padrao = [
        {'nome': 'Família', 'cor': 'success'},
        {'nome': 'Trabalho', 'cor': 'primary'},
        {'nome': 'Casa', 'cor': 'warning'},
        {'nome': 'Amigos', 'cor': 'info'},
        {'nome': 'Estudo', 'cor': 'secondary'},
        {'nome': 'Financeiro', 'cor': 'danger'},
        {'nome': 'Espiritual', 'cor': 'light'},
        {'nome': 'Saúde', 'cor': 'success'},
    ]

    for cat_data in categorias_padrao:
        categoria = Categoria(
            nome=cat_data['nome'],
            cor=cat_data['cor'],
            tenant_id=usuario.tenant_id,
            user_id=usuario.id,
        )
        db.session.add(categoria)

    db.session.commit()


def init_db():
    """Inicializa o banco de dados para uso local."""
    os.makedirs(app.instance_path, exist_ok=True)
    run_local_migrations(os.path.join(app.instance_path, app.config['DATABASE_FILENAME']))

    with app.app_context():
        db.create_all()

        for usuario in User.query.all():
            tem_categoria = Categoria.query.filter_by(
                tenant_id=usuario.tenant_id,
                user_id=usuario.id,
            ).first()
            if not tem_categoria:
                criar_categorias_padrao(usuario)


register_auth_routes(app, criar_categorias_padrao)
register_routes(app)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5050)
