from datetime import date, datetime
import json

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import contains_eager

from models import Categoria, Tarefa, db


def parse_notif_datetime(valor_str):
    """Converte datetime-local ('YYYY-MM-DDTHH:MM') para datetime."""
    if not valor_str:
        return None
    try:
        return datetime.strptime(valor_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        return None


def parse_date(valor_str):
    return datetime.strptime(valor_str, '%Y-%m-%d').date()


def parse_time(valor_str):
    return datetime.strptime(valor_str, '%H:%M').time()


def parse_optional_date(valor_str):
    return parse_date(valor_str) if valor_str else None


def parse_optional_time(valor_str):
    return parse_time(valor_str) if valor_str else None


def get_filtros_ativos():
    """Captura filtros ativos da URL ou sessao."""
    filtros = {
        'categoria': request.args.get('categoria', session.get('filtro_categoria', '')),
        'prioridade': request.args.get('prioridade', session.get('filtro_prioridade', '')),
        'status': request.args.get('status', session.get('filtro_status', '')),
        'data': request.args.get('data', session.get('filtro_data', '')),
        'busca': request.args.get('busca', session.get('filtro_busca', '')),
        'page': request.args.get('page', session.get('filtro_page', 1), type=int),
        'per_page': request.args.get('per_page', session.get('filtro_per_page', 10), type=int),
    }

    session['filtro_categoria'] = filtros['categoria']
    session['filtro_prioridade'] = filtros['prioridade']
    session['filtro_status'] = filtros['status']
    session['filtro_data'] = filtros['data']
    session['filtro_busca'] = filtros['busca']
    session['filtro_page'] = filtros['page']
    session['filtro_per_page'] = filtros['per_page']

    return filtros


def limpar_filtros_sessao():
    """Limpa todos os filtros da sessao."""
    session.pop('filtro_categoria', None)
    session.pop('filtro_prioridade', None)
    session.pop('filtro_status', None)
    session.pop('filtro_data', None)
    session.pop('filtro_busca', None)
    session.pop('filtro_page', None)
    session.pop('filtro_per_page', None)


def redirect_com_filtros(rota, **kwargs):
    """Redireciona mantendo os filtros ativos."""
    filtros = get_filtros_ativos()
    filtros.update(kwargs)
    filtros_limpos = {k: v for k, v in filtros.items() if v}
    return redirect(url_for(rota, **filtros_limpos))


def get_local_user():
    """Compatibilidade temporaria: retorna o usuario autenticado."""
    return current_user


def get_local_user_id():
    return current_user.id


def get_current_tenant_id():
    return current_user.tenant_id


def buscar_categoria_do_usuario(categoria_id):
    """Retorna categoria do usuario autenticado, sempre escopada por tenant."""
    if not categoria_id:
        return None
    return Categoria.query.filter_by(
        id=categoria_id,
        tenant_id=get_current_tenant_id(),
        user_id=get_local_user_id(),
    ).first()


def buscar_categoria_ou_404(categoria_id):
    return Categoria.query.filter_by(
        id=categoria_id,
        tenant_id=get_current_tenant_id(),
        user_id=get_local_user_id(),
    ).first_or_404()


def buscar_tarefa_ou_404(tarefa_id):
    return Tarefa.query.filter_by(
        id=tarefa_id,
        tenant_id=get_current_tenant_id(),
        user_id=get_local_user_id(),
    ).first_or_404()


def categorias_do_usuario():
    return Categoria.query.filter_by(
        tenant_id=get_current_tenant_id(),
        user_id=get_local_user_id(),
    ).order_by(Categoria.nome).all()


def categoria_existe_para_usuario(nome, categoria_id_ignorado=None):
    query = Categoria.query.filter(
        Categoria.nome == nome,
        Categoria.tenant_id == get_current_tenant_id(),
        Categoria.user_id == get_local_user_id(),
    )
    if categoria_id_ignorado is not None:
        query = query.filter(Categoria.id != categoria_id_ignorado)
    return query.first()


def dados_categoria_form():
    return {
        'nome': (request.form.get('nome') or '').strip(),
        'cor': request.form.get('cor', 'info'),
    }


def dados_tarefa_form():
    data_realizado = parse_optional_date(request.form.get('data_realizado'))
    hora_inicio = parse_time(request.form.get('hora_inicio'))
    hora_fim = parse_optional_time(request.form.get('hora_fim'))

    if hora_fim and hora_fim <= hora_inicio:
        raise ValueError('A hora de fim deve ser posterior à hora de início!')

    categoria = buscar_categoria_do_usuario(request.form.get('categoria_id', type=int))
    if not categoria:
        raise ValueError('Categoria inválida para este usuário.')

    return {
        'tarefa': request.form.get('tarefa'),
        'comentario': request.form.get('comentario', ''),
        'data_meta': parse_date(request.form.get('data_meta')),
        'data_realizado': data_realizado,
        'hora_inicio': hora_inicio,
        'hora_fim': hora_fim,
        'prioridade': request.form.get('prioridade'),
        'recorrencia': request.form.get('recorrencia'),
        'categoria': categoria,
        'status': 'Concluída' if data_realizado else 'Pendente',
        'notif_datetime_1': parse_notif_datetime(request.form.get('notif_datetime_1')),
        'notif_datetime_2': parse_notif_datetime(request.form.get('notif_datetime_2')),
    }


def montar_tarefa(dados):
    categoria = dados['categoria']
    return Tarefa(
        tarefa=dados['tarefa'],
        comentario=dados['comentario'],
        data_meta=dados['data_meta'],
        data_realizado=dados['data_realizado'],
        hora_inicio=dados['hora_inicio'],
        hora_fim=dados['hora_fim'],
        prioridade=dados['prioridade'],
        recorrencia=dados['recorrencia'],
        categoria_id=categoria.id,
        categoria_legado=categoria.nome,
        status=dados['status'],
        tenant_id=get_current_tenant_id(),
        user_id=get_local_user_id(),
        notif_datetime_1=dados['notif_datetime_1'],
        notif_email_enviada_1=False,
        notif_whatsapp_enviada_1=False,
        notif_datetime_2=dados['notif_datetime_2'],
        notif_email_enviada_2=False,
        notif_whatsapp_enviada_2=False,
    )


def aplicar_dados_tarefa(tarefa, dados):
    categoria = dados['categoria']
    tarefa.tarefa = dados['tarefa']
    tarefa.comentario = dados['comentario']
    tarefa.data_meta = dados['data_meta']
    tarefa.data_realizado = dados['data_realizado']
    tarefa.hora_inicio = dados['hora_inicio']
    tarefa.hora_fim = dados['hora_fim']
    tarefa.prioridade = dados['prioridade']
    tarefa.recorrencia = dados['recorrencia']
    tarefa.categoria_id = categoria.id
    tarefa.categoria_legado = categoria.nome
    tarefa.status = dados['status']

    if dados['notif_datetime_1'] != tarefa.notif_datetime_1:
        tarefa.notif_email_enviada_1 = False
        tarefa.notif_whatsapp_enviada_1 = False
    tarefa.notif_datetime_1 = dados['notif_datetime_1']

    if dados['notif_datetime_2'] != tarefa.notif_datetime_2:
        tarefa.notif_email_enviada_2 = False
        tarefa.notif_whatsapp_enviada_2 = False
    tarefa.notif_datetime_2 = dados['notif_datetime_2']


def register_routes(app):
    @app.route('/')
    @login_required
    def index():
        """Dashboard principal do MVP local."""
        return render_template('index.html')

    @app.route('/categorias')
    @login_required
    def lista_categorias():
        """Lista todas as categorias do usuario."""
        return render_template('lista_categorias.html', categorias=categorias_do_usuario())

    @app.route('/cadastro_categoria', methods=['GET', 'POST'])
    @login_required
    def cadastro_categoria():
        """Cadastro de nova categoria."""
        if request.method == 'POST':
            try:
                dados = dados_categoria_form()
                nome = dados['nome']
                existe = categoria_existe_para_usuario(nome)

                if existe:
                    flash(f'A categoria "{nome}" já existe!', 'warning')
                    return render_template('cadastro_categoria.html')

                nova_categoria = Categoria(
                    nome=nome,
                    cor=dados['cor'],
                    tenant_id=get_current_tenant_id(),
                    user_id=get_local_user_id(),
                )

                db.session.add(nova_categoria)
                db.session.commit()

                flash(f'Categoria "{nome}" criada com sucesso!', 'success')
                return redirect(url_for('lista_categorias'))

            except Exception as e:
                flash(f'Erro ao cadastrar categoria: {str(e)}', 'danger')

        return render_template('cadastro_categoria.html')

    @app.route('/editar_categoria/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_categoria(id):
        """Editar categoria existente."""
        categoria = buscar_categoria_ou_404(id)

        if request.method == 'POST':
            try:
                dados = dados_categoria_form()
                nome = dados['nome']
                existe = categoria_existe_para_usuario(nome, categoria_id_ignorado=id)

                if existe:
                    flash(f'Já existe outra categoria com o nome "{nome}"!', 'warning')
                    return render_template('editar_categoria.html', categoria=categoria)

                categoria.nome = nome
                categoria.cor = dados['cor']

                db.session.commit()
                flash(f'Categoria "{nome}" atualizada com sucesso!', 'success')
                return redirect(url_for('lista_categorias'))

            except Exception as e:
                flash(f'Erro ao atualizar categoria: {str(e)}', 'danger')

        return render_template('editar_categoria.html', categoria=categoria)

    @app.route('/deletar_categoria/<int:id>', methods=['POST'])
    @login_required
    def deletar_categoria(id):
        """Deletar categoria."""
        categoria = buscar_categoria_ou_404(id)

        tarefas_com_categoria = Tarefa.query.filter_by(
            tenant_id=get_current_tenant_id(),
            user_id=get_local_user_id(),
            categoria_id=categoria.id,
        ).count()

        if tarefas_com_categoria > 0:
            flash(f'Não é possível deletar "{categoria.nome}" pois há {tarefas_com_categoria} tarefa(s) usando esta categoria!', 'danger')
            return redirect(url_for('lista_categorias'))

        nome = categoria.nome
        db.session.delete(categoria)
        db.session.commit()

        flash(f'Categoria "{nome}" deletada com sucesso!', 'success')
        return redirect(url_for('lista_categorias'))

    @app.route('/cadastro_tarefa', methods=['GET', 'POST'])
    @login_required
    def cadastro_tarefa():
        """Cadastro de nova tarefa."""
        categorias = categorias_do_usuario()

        if request.method == 'POST':
            try:
                dados = dados_tarefa_form()
                nova_tarefa = montar_tarefa(dados)
            except ValueError as e:
                flash(str(e), 'danger')
                return render_template('cadastro_tarefa.html', categorias=categorias)
            except Exception as e:
                flash(f'Erro ao cadastrar tarefa: {str(e)}', 'danger')
            else:
                try:
                    db.session.add(nova_tarefa)
                    db.session.commit()

                    flash('Tarefa cadastrada com sucesso!', 'success')
                    return redirect_com_filtros('lista_tarefas')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao cadastrar tarefa: {str(e)}', 'danger')
                    return render_template('cadastro_tarefa.html', categorias=categorias)

        filtros = get_filtros_ativos()

        return render_template(
            'cadastro_tarefa.html',
            categorias=categorias,
            duplicate_id=request.args.get('duplicate'),
            tarefa=request.args.get('tarefa', ''),
            comentario=request.args.get('comentario', ''),
            hora_inicio=request.args.get('hora_inicio', ''),
            prioridade=request.args.get('prioridade', ''),
            recorrencia=request.args.get('recorrencia', ''),
            categoria_id=request.args.get('categoria_id', type=int),
            filtros=filtros,
        )

    @app.route('/lista_tarefas')
    @login_required
    def lista_tarefas():
        """Lista de tarefas com filtros e paginacao."""
        if request.args.get('limpar'):
            limpar_filtros_sessao()
            per_page = request.args.get('per_page', 10, type=int)
            return redirect(url_for('lista_tarefas', per_page=per_page))

        filtros = get_filtros_ativos()
        categorias = categorias_do_usuario()

        query = Tarefa.query.join(Tarefa.categoria).options(
            contains_eager(Tarefa.categoria)
        ).filter(
            Tarefa.tenant_id == get_current_tenant_id(),
            Tarefa.user_id == get_local_user_id(),
            Categoria.tenant_id == get_current_tenant_id(),
            Categoria.user_id == get_local_user_id(),
        )

        if filtros['categoria']:
            query = query.filter(Categoria.nome == filtros['categoria'])
        if filtros['prioridade']:
            query = query.filter(Tarefa.prioridade == filtros['prioridade'])
        if filtros['status']:
            query = query.filter(Tarefa.status == filtros['status'])
        if filtros['data']:
            data_obj = parse_date(filtros['data'])
            query = query.filter(Tarefa.data_meta == data_obj)
        if filtros['busca']:
            termo = f"%{filtros['busca']}%"
            query = query.filter(
                db.or_(
                    Tarefa.tarefa.ilike(termo),
                    func.coalesce(Tarefa.comentario, '').ilike(termo),
                )
            )

        tarefas_ordenadas = sorted(query.all(), key=lambda x: (x.data_meta, x.hora_inicio))
        page = filtros['page']
        per_page = filtros['per_page']
        total = len(tarefas_ordenadas)
        start = (page - 1) * per_page
        end = start + per_page
        tarefas_paginadas = tarefas_ordenadas[start:end]
        total_pages = (total + per_page - 1) // per_page

        return render_template(
            'lista_tarefas.html',
            tarefas=tarefas_paginadas,
            categorias=categorias,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total=total,
            categoria_filtro=filtros['categoria'],
            prioridade_filtro=filtros['prioridade'],
            status_filtro=filtros['status'],
            data_filtro=filtros['data'],
            busca_filtro=filtros['busca'],
        )

    @app.route('/editar_tarefa/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_tarefa(id):
        """Editar tarefa existente."""
        tarefa = buscar_tarefa_ou_404(id)
        categorias = categorias_do_usuario()

        if request.method == 'POST':
            try:
                dados = dados_tarefa_form()
                aplicar_dados_tarefa(tarefa, dados)
                db.session.commit()
                flash('Tarefa atualizada com sucesso!', 'success')
                return redirect_com_filtros('lista_tarefas')

            except ValueError as e:
                flash(str(e), 'danger')
                return render_template('editar_tarefa.html', tarefa=tarefa, categorias=categorias)
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar tarefa: {str(e)}', 'danger')

        return render_template('editar_tarefa.html', tarefa=tarefa, categorias=categorias, filtros=get_filtros_ativos())

    @app.route('/duplicar_tarefa/<int:id>')
    @login_required
    def duplicar_tarefa(id):
        """Duplica uma tarefa existente para facilitar recriacao."""
        tarefa = buscar_tarefa_ou_404(id)

        return redirect(url_for(
            'cadastro_tarefa',
            duplicate=id,
            tarefa=tarefa.tarefa,
            comentario=tarefa.comentario,
            hora_inicio=tarefa.hora_inicio.strftime('%H:%M'),
            prioridade=tarefa.prioridade,
            recorrencia=tarefa.recorrencia,
            categoria_id=tarefa.categoria_id,
        ))

    @app.route('/deletar_tarefa/<int:id>', methods=['POST'])
    @login_required
    def deletar_tarefa(id):
        """Deletar tarefa."""
        tarefa = buscar_tarefa_ou_404(id)
        db.session.delete(tarefa)
        db.session.commit()

        flash('Tarefa deletada com sucesso!', 'success')
        return redirect_com_filtros('lista_tarefas')

    @app.route('/marcar_concluida/<int:id>', methods=['POST'])
    @login_required
    def marcar_concluida(id):
        """Marcar tarefa como concluida."""
        tarefa = buscar_tarefa_ou_404(id)
        tarefa.status = 'Concluída'
        tarefa.data_realizado = date.today()
        db.session.commit()

        flash('Tarefa marcada como concluída!', 'success')
        return redirect_com_filtros('lista_tarefas')

    @app.route('/calendario')
    @login_required
    def calendario():
        """Calendario de tarefas."""
        tarefas = Tarefa.query.join(Tarefa.categoria).options(
            contains_eager(Tarefa.categoria)
        ).filter(
            Tarefa.tenant_id == get_current_tenant_id(),
            Tarefa.user_id == get_local_user_id(),
            Categoria.tenant_id == get_current_tenant_id(),
            Categoria.user_id == get_local_user_id(),
        ).all()
        categorias = categorias_do_usuario()

        tarefas_json = json.dumps([{
            'id': t.id,
            'tarefa': t.tarefa,
            'comentario': t.comentario or '',
            'data_meta': t.data_meta.strftime('%Y-%m-%d'),
            'hora_inicio': t.hora_inicio.strftime('%H:%M'),
            'hora_fim': t.hora_fim.strftime('%H:%M') if t.hora_fim else '',
            'prioridade': t.prioridade,
            'categoria_id': t.categoria_id,
            'categoria': t.categoria.nome,
            'status': t.status,
        } for t in tarefas], ensure_ascii=False)

        categorias_json = json.dumps([{
            'id': c.id,
            'nome': c.nome,
            'cor': c.cor,
        } for c in categorias], ensure_ascii=False)

        return render_template(
            'calendario.html',
            tarefas_json=tarefas_json,
            categorias_json=categorias_json,
        )

    @app.route('/entrada_rapida')
    @login_required
    def entrada_rapida():
        """Pagina de entrada rapida de tarefa por texto livre."""
        categorias_json = json.dumps(
            [{'id': c.id, 'nome': c.nome, 'cor': c.cor} for c in categorias_do_usuario()],
            ensure_ascii=False,
        )
        return render_template('entrada_rapida.html', categorias_json=categorias_json)

    @app.route('/mover_tarefa/<int:id>', methods=['POST'])
    @login_required
    def mover_tarefa(id):
        """Move a data_meta de uma tarefa usado pelo drag and drop do calendario."""
        tarefa = buscar_tarefa_ou_404(id)
        data = request.get_json() or {}
        nova_data_str = data.get('data_meta')

        if not nova_data_str:
            return jsonify({'ok': False, 'erro': 'Data inválida'}), 400

        try:
            tarefa.data_meta = parse_date(nova_data_str)
        except ValueError:
            return jsonify({'ok': False, 'erro': 'Formato de data inválido'}), 400

        db.session.commit()
        return jsonify({'ok': True})
