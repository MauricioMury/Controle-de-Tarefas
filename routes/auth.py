from datetime import timedelta
import re

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import Tenant, User, agora_utc, db


MAX_LOGIN_ATTEMPTS = 10
LOCKOUT_MINUTES = 20


def _slugify(value):
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or 'tenant-local'


def _tenant_slug_disponivel(base_slug):
    slug = base_slug
    suffix = 2
    while Tenant.query.filter_by(slug=slug).first():
        slug = f'{base_slug}-{suffix}'
        suffix += 1
    return slug


def _validar_senha(password):
    erros = []
    if len(password or '') < 12:
        erros.append('ter pelo menos 12 caracteres')
    if not re.search(r'[A-Z]', password or ''):
        erros.append('conter letra maiúscula')
    if not re.search(r'[a-z]', password or ''):
        erros.append('conter letra minúscula')
    if not re.search(r'\d', password or ''):
        erros.append('conter número')
    if not re.search(r'[^A-Za-z0-9]', password or ''):
        erros.append('conter símbolo')
    return erros


def _user_bloqueado(user):
    return user.locked_until and user.locked_until > agora_utc()


def _next_url_segura():
    next_url = request.args.get('next')
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        return next_url
    return url_for('index')


def register_auth_routes(app, criar_categorias_padrao):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = (request.form.get('username') or '').strip()
            password = request.form.get('password') or ''
            user = User.query.filter_by(username=username).first()

            if not user:
                flash('Usuário ou senha inválidos.', 'danger')
                return render_template('login.html')

            if _user_bloqueado(user):
                minutos = max(1, int((user.locked_until - agora_utc()).total_seconds() // 60) + 1)
                flash(f'Conta bloqueada temporariamente. Tente novamente em {minutos} minuto(s).', 'danger')
                return render_template('login.html')

            if not check_password_hash(user.password, password):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                    user.locked_until = agora_utc() + timedelta(minutes=LOCKOUT_MINUTES)
                    flash('Conta bloqueada após 10 tentativas inválidas. Tente novamente em 20 minutos.', 'danger')
                else:
                    restantes = MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
                    flash(f'Usuário ou senha inválidos. Tentativas restantes: {restantes}.', 'danger')
                db.session.commit()
                return render_template('login.html')

            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()
            login_user(user)
            return redirect(_next_url_segura())

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = (request.form.get('username') or '').strip()
            password = request.form.get('password') or ''
            confirm_password = request.form.get('confirm_password') or ''

            if not username:
                flash('Informe um usuário.', 'danger')
                return render_template('register.html')

            if User.query.filter_by(username=username).first():
                flash('Já existe uma conta com este usuário.', 'danger')
                return render_template('register.html')

            if password != confirm_password:
                flash('A confirmação de senha não confere.', 'danger')
                return render_template('register.html')

            erros_senha = _validar_senha(password)
            if erros_senha:
                flash('A senha deve ' + ', '.join(erros_senha) + '.', 'danger')
                return render_template('register.html')

            tenant = Tenant(
                nome=f'Tenant {username}',
                slug=_tenant_slug_disponivel(_slugify(username)),
            )
            db.session.add(tenant)
            db.session.flush()

            user = User(
                username=username,
                password=generate_password_hash(password),
                tenant_id=tenant.id,
            )
            db.session.add(user)
            db.session.flush()
            criar_categorias_padrao(user)

            login_user(user)
            flash('Conta criada com sucesso.', 'success')
            return redirect(url_for('index'))

        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Sessão encerrada.', 'success')
        return redirect(url_for('login'))

    @app.route('/perfil', methods=['GET', 'POST'])
    @login_required
    def perfil():
        if request.method == 'POST':
            current_user.email_notif = (request.form.get('email_notif') or '').strip() or None
            current_user.whatsapp_numero = (request.form.get('whatsapp_numero') or '').strip() or None
            current_user.whatsapp_apikey = (request.form.get('whatsapp_apikey') or '').strip() or None
            db.session.commit()
            flash('Perfil atualizado com sucesso.', 'success')
            return redirect(url_for('perfil'))

        return render_template('perfil.html')
