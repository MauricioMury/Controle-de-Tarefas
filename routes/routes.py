from datetime import date, datetime, timedelta, timezone
import json

from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import case, func
from sqlalchemy.orm import contains_eager

from models import Categoria, Etapa, HistoricoEtapa, Tarefa, db


STATUS_ETAPA_CRIADA = 'Criada'
STATUS_ETAPA_INICIADA = 'Iniciada'
STATUS_ETAPA_PAUSADA = 'Pausada'
STATUS_ETAPA_CONCLUIDA = 'Concluida'
STATUS_ETAPA_PERMITIDOS = {
    STATUS_ETAPA_CRIADA,
    STATUS_ETAPA_INICIADA,
    STATUS_ETAPA_PAUSADA,
    STATUS_ETAPA_CONCLUIDA,
}

ACOES_HISTORICO_ETAPA = {
    'criar',
    'editar',
    'iniciar',
    'pausar',
    'retomar',
    'concluir',
    'excluir',
    'reordenar',
}

TRANSICOES_STATUS_ETAPA = {
    STATUS_ETAPA_CRIADA: {STATUS_ETAPA_INICIADA},
    STATUS_ETAPA_INICIADA: {STATUS_ETAPA_PAUSADA, STATUS_ETAPA_CONCLUIDA},
    STATUS_ETAPA_PAUSADA: {STATUS_ETAPA_INICIADA, STATUS_ETAPA_CONCLUIDA},
    STATUS_ETAPA_CONCLUIDA: set(),
}

# Brasil sem horario de verao desde 2019; offset fixo evita depender do pacote tzdata no Windows.
FUSO_SAO_PAULO = timezone(timedelta(hours=-3), 'America/Sao_Paulo')

OPCOES_POR_PAGINA = (5, 10, 20, 50, 100)
POR_PAGINA_PADRAO = 10
PARAMETROS_FILTRO_LISTA = ('categoria', 'prioridade', 'status', 'data', 'busca', 'per_page')


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
    per_page = request.args.get('per_page', session.get('filtro_per_page', POR_PAGINA_PADRAO), type=int)
    if per_page not in OPCOES_POR_PAGINA:
        per_page = POR_PAGINA_PADRAO

    page = request.args.get('page', session.get('filtro_page', 1), type=int)
    if not page or page < 1:
        page = 1

    filtros = {
        'categoria': request.args.get('categoria', session.get('filtro_categoria', '')),
        'prioridade': request.args.get('prioridade', session.get('filtro_prioridade', '')),
        'status': request.args.get('status', session.get('filtro_status', '')),
        'data': request.args.get('data', session.get('filtro_data', '')),
        'busca': request.args.get('busca', session.get('filtro_busca', '')),
        'page': page,
        'per_page': per_page,
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


def filtros_da_sessao():
    """Filtros de Minhas Tarefas gravados na sessao, sem ler a URL nem gravar nada.

    Usado nas telas de cadastro/edicao, cuja URL traz campos de pre-preenchimento
    (ex.: prioridade da tarefa duplicada) que nao sao filtros.
    """
    return {
        'categoria': session.get('filtro_categoria', ''),
        'prioridade': session.get('filtro_prioridade', ''),
        'status': session.get('filtro_status', ''),
        'data': session.get('filtro_data', ''),
        'busca': session.get('filtro_busca', ''),
        'page': session.get('filtro_page', 1),
        'per_page': session.get('filtro_per_page', POR_PAGINA_PADRAO),
    }


def url_retorno_segura(valor):
    """Aceita so caminhos internos ('/calendario?...'); recusa URLs externas (open redirect)."""
    if not valor or len(valor) > 2000:
        return None
    if not valor.startswith('/') or valor.startswith('//') or '\\' in valor:
        return None
    if any(ord(c) < 32 for c in valor):
        return None
    return valor


def destino_retorno():
    """Tela de origem informada em 'next' (formulario ou URL), se for segura."""
    return url_retorno_segura(request.form.get('next') or request.args.get('next'))


def redirect_retorno(rota_padrao):
    """Volta para a tela de origem; sem ela, para a rota padrao com os filtros ativos."""
    destino = destino_retorno()
    if destino:
        return redirect(destino)
    return redirect_com_filtros(rota_padrao)


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


def buscar_etapa_ou_404(etapa_id):
    return Etapa.query.join(Tarefa, Etapa.tarefa_id == Tarefa.id).filter(
        Etapa.id == etapa_id,
        Etapa.tenant_id == get_current_tenant_id(),
        Etapa.user_id == get_local_user_id(),
        Tarefa.tenant_id == get_current_tenant_id(),
        Tarefa.user_id == get_local_user_id(),
    ).first_or_404()


def etapas_da_tarefa_query(tarefa):
    return Etapa.query.filter_by(
        tarefa_id=tarefa.id,
        tenant_id=get_current_tenant_id(),
        user_id=get_local_user_id(),
    ).order_by(Etapa.ordem)


def proxima_ordem_etapa(tarefa):
    maior_ordem = db.session.query(func.max(Etapa.ordem)).filter_by(
        tarefa_id=tarefa.id,
        tenant_id=get_current_tenant_id(),
        user_id=get_local_user_id(),
    ).scalar()
    return (maior_ordem or 0) + 1


def calcular_progresso_tarefa(tarefa):
    etapas = etapas_da_tarefa_query(tarefa).all()
    total = len(etapas)
    concluidas = sum(1 for etapa in etapas if etapa.status == STATUS_ETAPA_CONCLUIDA)
    progresso = int((concluidas / total) * 100) if total else 0
    return {
        'total': total,
        'concluidas': concluidas,
        'progresso': progresso,
    }


def calcular_progressos_tarefas(tarefas):
    tarefa_ids = [tarefa.id for tarefa in tarefas]
    if not tarefa_ids:
        return {}

    linhas = db.session.query(
        Etapa.tarefa_id,
        func.count(Etapa.id).label('total'),
        func.sum(
            case(
                (Etapa.status == STATUS_ETAPA_CONCLUIDA, 1),
                else_=0,
            )
        ).label('concluidas'),
    ).filter(
        Etapa.tarefa_id.in_(tarefa_ids),
        Etapa.tenant_id == get_current_tenant_id(),
        Etapa.user_id == get_local_user_id(),
    ).group_by(Etapa.tarefa_id).all()

    progressos = {
        tarefa_id: {
            'total': 0,
            'concluidas': 0,
            'progresso': 0,
        }
        for tarefa_id in tarefa_ids
    }

    for linha in linhas:
        total = linha.total or 0
        concluidas = linha.concluidas or 0
        progressos[linha.tarefa_id] = {
            'total': total,
            'concluidas': concluidas,
            'progresso': int((concluidas / total) * 100) if total else 0,
        }

    return progressos


def validar_status_etapa(status):
    if status not in STATUS_ETAPA_PERMITIDOS:
        raise ValueError('Status de etapa inválido.')


def validar_acao_historico_etapa(acao):
    if acao not in ACOES_HISTORICO_ETAPA:
        raise ValueError('Ação de histórico de etapa inválida.')


def registrar_historico_etapa(etapa, acao, descricao=None):
    validar_acao_historico_etapa(acao)
    historico = HistoricoEtapa(
        tarefa_id=etapa.tarefa_id,
        etapa_id=etapa.id,
        tenant_id=etapa.tenant_id,
        user_id=etapa.user_id,
        acao=acao,
        descricao=descricao,
    )
    db.session.add(historico)
    return historico


def criar_etapa(tarefa, dados):
    titulo = (dados.get('titulo') or '').strip()
    if not titulo:
        raise ValueError('Informe o título da etapa.')

    status = dados.get('status') or STATUS_ETAPA_CRIADA
    validar_status_etapa(status)

    hora_inicio = dados.get('hora_inicio')
    hora_fim = dados.get('hora_fim')
    if hora_inicio and hora_fim and hora_fim <= hora_inicio:
        raise ValueError('A hora de fim da etapa deve ser posterior à hora de início.')

    etapa = Etapa(
        tarefa_id=tarefa.id,
        tenant_id=tarefa.tenant_id,
        user_id=tarefa.user_id,
        titulo=titulo,
        descricao=(dados.get('descricao') or '').strip() or None,
        ordem=dados.get('ordem') or proxima_ordem_etapa(tarefa),
        data_planejada=dados.get('data_planejada'),
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
        status=status,
        concluida_em=datetime.utcnow() if status == STATUS_ETAPA_CONCLUIDA else None,
    )
    db.session.add(etapa)
    db.session.flush()
    registrar_historico_etapa(etapa, 'criar', 'Etapa criada.')
    return etapa


def copiar_etapas_para_tarefa(tarefa_origem, tarefa_destino):
    etapas_origem = etapas_da_tarefa_query(tarefa_origem).all()
    etapas_copiadas = []
    for etapa_origem in etapas_origem:
        etapa_copiada = criar_etapa(tarefa_destino, {
            'titulo': etapa_origem.titulo,
            'descricao': etapa_origem.descricao,
            'ordem': etapa_origem.ordem,
            'data_planejada': tarefa_destino.data_meta,
            'hora_inicio': etapa_origem.hora_inicio,
            'hora_fim': etapa_origem.hora_fim,
            'status': STATUS_ETAPA_CRIADA,
        })
        etapas_copiadas.append(etapa_copiada)
    return etapas_copiadas


def aplicar_dados_etapa(etapa, dados):
    titulo = (dados.get('titulo') or '').strip()
    if not titulo:
        raise ValueError('Informe o título da etapa.')

    hora_inicio = dados.get('hora_inicio')
    hora_fim = dados.get('hora_fim')
    if hora_inicio and hora_fim and hora_fim <= hora_inicio:
        raise ValueError('A hora de fim da etapa deve ser posterior à hora de início.')

    etapa.titulo = titulo
    etapa.descricao = (dados.get('descricao') or '').strip() or None
    etapa.data_planejada = dados.get('data_planejada')
    etapa.hora_inicio = hora_inicio
    etapa.hora_fim = hora_fim
    etapa.updated_at = datetime.utcnow()
    registrar_historico_etapa(etapa, 'editar', 'Etapa editada.')
    return etapa


def alterar_status_etapa(etapa, novo_status, descricao=None):
    validar_status_etapa(novo_status)
    status_atual = etapa.status
    if novo_status == status_atual:
        return etapa
    if novo_status not in TRANSICOES_STATUS_ETAPA.get(status_atual, set()):
        raise ValueError(f'Transição de status inválida: {status_atual} -> {novo_status}.')

    etapa.status = novo_status
    etapa.updated_at = datetime.utcnow()
    if novo_status == STATUS_ETAPA_INICIADA and not etapa.hora_inicio:
        etapa.hora_inicio = datetime.utcnow().time().replace(microsecond=0)
    if novo_status == STATUS_ETAPA_CONCLUIDA:
        agora = datetime.utcnow()
        etapa.concluida_em = agora
        if not etapa.hora_fim:
            etapa.hora_fim = agora.time().replace(microsecond=0)

    acao_por_status = {
        STATUS_ETAPA_INICIADA: 'iniciar' if status_atual == STATUS_ETAPA_CRIADA else 'retomar',
        STATUS_ETAPA_PAUSADA: 'pausar',
        STATUS_ETAPA_CONCLUIDA: 'concluir',
    }
    registrar_historico_etapa(
        etapa,
        acao_por_status[novo_status],
        descricao or f'Status alterado de {status_atual} para {novo_status}.',
    )
    return etapa


def reordenar_etapas(tarefa, etapas_ordenadas):
    ids_informados = [etapa_id for etapa_id, _ordem in etapas_ordenadas]
    etapas = Etapa.query.filter(
        Etapa.tarefa_id == tarefa.id,
        Etapa.tenant_id == get_current_tenant_id(),
        Etapa.user_id == get_local_user_id(),
        Etapa.id.in_(ids_informados),
    ).all()
    etapas_por_id = {etapa.id: etapa for etapa in etapas}

    if len(etapas_por_id) != len(set(ids_informados)):
        raise ValueError('Lista de etapas inválida para esta tarefa.')

    ordens = [ordem for _etapa_id, ordem in etapas_ordenadas]
    if len(ordens) != len(set(ordens)):
        raise ValueError('A ordem das etapas não pode conter duplicidade.')

    for indice, etapa_id in enumerate(ids_informados, start=1):
        etapa = etapas_por_id[etapa_id]
        etapa.ordem = -indice
    db.session.flush()

    for etapa_id, ordem in etapas_ordenadas:
        etapa = etapas_por_id[etapa_id]
        etapa.ordem = ordem
        etapa.updated_at = datetime.utcnow()
        registrar_historico_etapa(etapa, 'reordenar', f'Ordem alterada para {ordem}.')

    return list(etapas_por_id.values())


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


def etapa_to_dict(etapa):
    return {
        'id': etapa.id,
        'tarefa_id': etapa.tarefa_id,
        'titulo': etapa.titulo,
        'descricao': etapa.descricao or '',
        'ordem': etapa.ordem,
        'data_planejada': etapa.data_planejada.strftime('%Y-%m-%d') if etapa.data_planejada else '',
        'hora_inicio': etapa.hora_inicio.strftime('%H:%M') if etapa.hora_inicio else '',
        'hora_fim': etapa.hora_fim.strftime('%H:%M') if etapa.hora_fim else '',
        'status': etapa.status,
        'concluida_em': etapa.concluida_em.isoformat() if etapa.concluida_em else '',
        'created_at': etapa.created_at.isoformat() if etapa.created_at else '',
        'updated_at': etapa.updated_at.isoformat() if etapa.updated_at else '',
    }


def historico_etapa_to_dict(historico):
    return {
        'id': historico.id,
        'tarefa_id': historico.tarefa_id,
        'etapa_id': historico.etapa_id,
        'acao': historico.acao,
        'descricao': historico.descricao or '',
        'created_at': historico.created_at.isoformat() if historico.created_at else '',
    }


def quer_resposta_json():
    return request.is_json or request.args.get('format') == 'json' or (
        request.accept_mimetypes.best == 'application/json'
        and request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']
    )


def dados_etapa_request():
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    ordem_valor = data.get('ordem')
    return {
        'titulo': data.get('titulo'),
        'descricao': data.get('descricao', ''),
        'ordem': int(ordem_valor) if ordem_valor else None,
        'data_planejada': parse_optional_date(data.get('data_planejada')),
        'hora_inicio': parse_optional_time(data.get('hora_inicio')),
        'hora_fim': parse_optional_time(data.get('hora_fim')),
        'status': data.get('status') or STATUS_ETAPA_CRIADA,
    }


def resposta_etapa_salva(tarefa_id, mensagem):
    if request.is_json:
        return jsonify({'ok': True, 'mensagem': mensagem})
    flash(mensagem, 'success')
    return redirect(destino_retorno() or url_for('listar_etapas_tarefa', id=tarefa_id))


def resposta_erro_etapa(mensagem, status_code=400):
    if request.is_json:
        return jsonify({'ok': False, 'erro': mensagem}), status_code
    flash(mensagem, 'danger')
    return redirect(request.referrer or url_for('lista_tarefas'))


def alterar_status_etapa_route(etapa_id, novo_status, mensagem):
    etapa = buscar_etapa_ou_404(etapa_id)
    try:
        alterar_status_etapa(etapa, novo_status)
        db.session.commit()
        if request.is_json:
            return jsonify({'ok': True, 'mensagem': mensagem, 'etapa': etapa_to_dict(etapa)})
        return resposta_etapa_salva(etapa.tarefa_id, mensagem)
    except ValueError as e:
        db.session.rollback()
        return resposta_erro_etapa(str(e), 400)
    except Exception as e:
        db.session.rollback()
        return resposta_erro_etapa(f'Erro ao alterar status da etapa: {str(e)}', 500)


def hoje_sao_paulo():
    """Data atual em Sao Paulo (o servidor de producao roda em UTC)."""
    return datetime.now(FUSO_SAO_PAULO).date()


def indicadores_dashboard():
    """Conta as tarefas do usuario para o Inicio, sem usar os filtros da sessao."""
    def contar(condicao):
        return func.coalesce(func.sum(case((condicao, 1), else_=0)), 0)

    total, pendentes, concluidas, alta_prioridade, hoje = db.session.query(
        func.count(Tarefa.id),
        contar(Tarefa.status == 'Pendente'),
        contar(Tarefa.status == 'Concluída'),
        contar(Tarefa.prioridade == 'Muito Importante'),
        contar(Tarefa.data_meta == hoje_sao_paulo()),
    ).filter(
        Tarefa.tenant_id == get_current_tenant_id(),
        Tarefa.user_id == get_local_user_id(),
    ).one()

    return {
        'total': total,
        'pendentes': pendentes,
        'concluidas': concluidas,
        'alta_prioridade': alta_prioridade,
        'hoje': hoje,
    }


def register_routes(app):
    @app.route('/')
    @login_required
    def index():
        """Dashboard principal: indicadores independentes dos filtros de Minhas Tarefas."""
        return render_template('index.html', indicadores=indicadores_dashboard())

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
        filtros = filtros_da_sessao()
        next_url = destino_retorno()

        if request.method == 'POST':
            try:
                dados = dados_tarefa_form()
                nova_tarefa = montar_tarefa(dados)
                tarefa_origem = None
                duplicate_id = request.form.get('duplicate_id', type=int)
                if duplicate_id:
                    tarefa_origem = buscar_tarefa_ou_404(duplicate_id)
            except ValueError as e:
                flash(str(e), 'danger')
                return render_template('cadastro_tarefa.html', categorias=categorias, filtros=filtros, next_url=next_url)
            except Exception as e:
                flash(f'Erro ao cadastrar tarefa: {str(e)}', 'danger')
            else:
                try:
                    db.session.add(nova_tarefa)
                    db.session.flush()
                    if tarefa_origem:
                        copiar_etapas_para_tarefa(tarefa_origem, nova_tarefa)
                    db.session.commit()

                    if tarefa_origem:
                        flash('Tarefa e etapas duplicadas com sucesso!', 'success')
                    else:
                        flash('Tarefa cadastrada com sucesso!', 'success')
                    return redirect_retorno('lista_tarefas')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Erro ao cadastrar tarefa: {str(e)}', 'danger')
                    return render_template('cadastro_tarefa.html', categorias=categorias, filtros=filtros, next_url=next_url)

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
            next_url=next_url,
        )

    @app.route('/lista_tarefas')
    @login_required
    def lista_tarefas():
        """Lista de tarefas com filtros e paginacao."""
        if request.args.get('limpar'):
            limpar_filtros_sessao()
            per_page = request.args.get('per_page', POR_PAGINA_PADRAO, type=int)
            if per_page not in OPCOES_POR_PAGINA:
                per_page = POR_PAGINA_PADRAO
            return redirect(url_for('lista_tarefas', per_page=per_page))

        # Filtro ou itens por pagina enviados sem pagina: recomeca na primeira.
        if 'page' not in request.args and any(p in request.args for p in PARAMETROS_FILTRO_LISTA):
            session['filtro_page'] = 1

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

        per_page = filtros['per_page']
        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(filtros['page'], total_pages)
        session['filtro_page'] = page

        tarefas_paginadas = query.order_by(
            Tarefa.data_meta, Tarefa.hora_inicio, Tarefa.id
        ).offset((page - 1) * per_page).limit(per_page).all()
        progressos_por_tarefa = calcular_progressos_tarefas(tarefas_paginadas)

        return render_template(
            'lista_tarefas.html',
            tarefas=tarefas_paginadas,
            progressos_por_tarefa=progressos_por_tarefa,
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
        next_url = destino_retorno()

        def renderizar_edicao():
            return render_template(
                'editar_tarefa.html',
                tarefa=tarefa,
                categorias=categorias,
                progresso=calcular_progresso_tarefa(tarefa),
                filtros=filtros_da_sessao(),
                next_url=next_url,
            )

        if request.method == 'POST':
            try:
                dados = dados_tarefa_form()
                aplicar_dados_tarefa(tarefa, dados)
                db.session.commit()
                flash('Tarefa atualizada com sucesso!', 'success')
                return redirect_retorno('lista_tarefas')

            except ValueError as e:
                db.session.rollback()
                flash(str(e), 'danger')
                return renderizar_edicao()
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar tarefa: {str(e)}', 'danger')

        return renderizar_edicao()

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
            next=destino_retorno(),
        ))

    @app.route('/deletar_tarefa/<int:id>', methods=['POST'])
    @login_required
    def deletar_tarefa(id):
        """Deletar tarefa."""
        tarefa = buscar_tarefa_ou_404(id)
        db.session.delete(tarefa)
        db.session.commit()

        flash('Tarefa deletada com sucesso!', 'success')
        return redirect_retorno('lista_tarefas')

    @app.route('/marcar_concluida/<int:id>', methods=['POST'])
    @login_required
    def marcar_concluida(id):
        """Marcar tarefa como concluida."""
        tarefa = buscar_tarefa_ou_404(id)
        tarefa.status = 'Concluída'
        tarefa.data_realizado = date.today()
        db.session.commit()

        flash('Tarefa marcada como concluída!', 'success')
        return redirect_retorno('lista_tarefas')

    @app.route('/tarefas/<int:id>/etapas')
    @login_required
    def listar_etapas_tarefa(id):
        """Lista etapas da tarefa."""
        tarefa = buscar_tarefa_ou_404(id)
        etapas = etapas_da_tarefa_query(tarefa).all()
        progresso = calcular_progresso_tarefa(tarefa)
        if quer_resposta_json():
            return jsonify({
                'ok': True,
                'tarefa': {
                    'id': tarefa.id,
                    'titulo': tarefa.tarefa,
                    'status': tarefa.status,
                    'data_meta': tarefa.data_meta.strftime('%Y-%m-%d'),
                },
                'progresso': progresso,
                'etapas': [etapa_to_dict(etapa) for etapa in etapas],
            })
        return render_template(
            'lista_etapas.html',
            tarefa=tarefa,
            etapas=etapas,
            progresso=progresso,
            transicoes_status=TRANSICOES_STATUS_ETAPA,
            next_url=destino_retorno(),
        )

    @app.route('/tarefas/<int:id>/etapas/nova', methods=['GET', 'POST'])
    @login_required
    def nova_etapa(id):
        """Cria etapa para uma tarefa."""
        tarefa = buscar_tarefa_ou_404(id)
        if request.method == 'GET':
            proxima_ordem = proxima_ordem_etapa(tarefa)
            if quer_resposta_json():
                return jsonify({
                    'ok': True,
                    'tarefa_id': tarefa.id,
                    'proxima_ordem': proxima_ordem,
                    'status_permitidos': sorted(STATUS_ETAPA_PERMITIDOS),
                })
            return render_template(
                'cadastro_etapa.html',
                tarefa=tarefa,
                proxima_ordem=proxima_ordem,
                status_permitidos=sorted(STATUS_ETAPA_PERMITIDOS),
            )

        try:
            etapa = criar_etapa(tarefa, dados_etapa_request())
            db.session.commit()
            if request.is_json:
                return jsonify({'ok': True, 'mensagem': 'Etapa criada com sucesso.', 'etapa': etapa_to_dict(etapa)}), 201
            return resposta_etapa_salva(tarefa.id, 'Etapa criada com sucesso.')
        except ValueError as e:
            db.session.rollback()
            return resposta_erro_etapa(str(e), 400)
        except Exception as e:
            db.session.rollback()
            return resposta_erro_etapa(f'Erro ao criar etapa: {str(e)}', 500)

    @app.route('/etapas/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_etapa(id):
        """Edita etapa existente."""
        etapa = buscar_etapa_ou_404(id)
        if request.method == 'GET':
            if quer_resposta_json():
                return jsonify({'ok': True, 'etapa': etapa_to_dict(etapa)})
            return render_template(
                'editar_etapa.html',
                tarefa=etapa.tarefa_ref,
                etapa=etapa,
                next_url=destino_retorno(),
            )

        try:
            aplicar_dados_etapa(etapa, dados_etapa_request())
            db.session.commit()
            if request.is_json:
                return jsonify({'ok': True, 'mensagem': 'Etapa atualizada com sucesso.', 'etapa': etapa_to_dict(etapa)})
            return resposta_etapa_salva(etapa.tarefa_id, 'Etapa atualizada com sucesso.')
        except ValueError as e:
            db.session.rollback()
            return resposta_erro_etapa(str(e), 400)
        except Exception as e:
            db.session.rollback()
            return resposta_erro_etapa(f'Erro ao atualizar etapa: {str(e)}', 500)

    @app.route('/etapas/<int:id>/iniciar', methods=['POST'])
    @login_required
    def iniciar_etapa(id):
        return alterar_status_etapa_route(id, STATUS_ETAPA_INICIADA, 'Etapa iniciada com sucesso.')

    @app.route('/etapas/<int:id>/pausar', methods=['POST'])
    @login_required
    def pausar_etapa(id):
        return alterar_status_etapa_route(id, STATUS_ETAPA_PAUSADA, 'Etapa pausada com sucesso.')

    @app.route('/etapas/<int:id>/retomar', methods=['POST'])
    @login_required
    def retomar_etapa(id):
        return alterar_status_etapa_route(id, STATUS_ETAPA_INICIADA, 'Etapa retomada com sucesso.')

    @app.route('/etapas/<int:id>/concluir', methods=['POST'])
    @login_required
    def concluir_etapa(id):
        return alterar_status_etapa_route(id, STATUS_ETAPA_CONCLUIDA, 'Etapa concluída com sucesso.')

    @app.route('/etapas/<int:id>/deletar', methods=['POST'])
    @login_required
    def deletar_etapa(id):
        etapa = buscar_etapa_ou_404(id)
        tarefa_id = etapa.tarefa_id
        try:
            HistoricoEtapa.query.filter_by(
                etapa_id=etapa.id,
                tenant_id=get_current_tenant_id(),
                user_id=get_local_user_id(),
            ).delete(synchronize_session=False)
            db.session.delete(etapa)
            db.session.commit()
            return resposta_etapa_salva(tarefa_id, 'Etapa deletada com sucesso.')
        except Exception as e:
            db.session.rollback()
            return resposta_erro_etapa(f'Erro ao deletar etapa: {str(e)}', 500)

    @app.route('/etapas/<int:id>/historico')
    @login_required
    def historico_etapa(id):
        etapa = buscar_etapa_ou_404(id)
        historicos = HistoricoEtapa.query.filter_by(
            etapa_id=etapa.id,
            tarefa_id=etapa.tarefa_id,
            tenant_id=get_current_tenant_id(),
            user_id=get_local_user_id(),
        ).order_by(HistoricoEtapa.created_at.desc(), HistoricoEtapa.id.desc()).all()
        if quer_resposta_json():
            return jsonify({
                'ok': True,
                'etapa': etapa_to_dict(etapa),
                'historico': [historico_etapa_to_dict(historico) for historico in historicos],
            })
        return render_template(
            'historico_etapa.html',
            tarefa=etapa.tarefa_ref,
            etapa=etapa,
            historicos=historicos,
        )

    @app.route('/tarefas/<int:id>/etapas/reordenar', methods=['POST'])
    @login_required
    def reordenar_etapas_tarefa(id):
        tarefa = buscar_tarefa_ou_404(id)
        data = request.get_json(silent=True) or {}
        etapas_payload = data.get('etapas') or []
        try:
            etapas_ordenadas = [
                (int(item['id']), int(item['ordem']))
                for item in etapas_payload
            ]
            etapas = reordenar_etapas(tarefa, etapas_ordenadas)
            db.session.commit()
            return jsonify({
                'ok': True,
                'mensagem': 'Etapas reordenadas com sucesso.',
                'etapas': [etapa_to_dict(etapa) for etapa in sorted(etapas, key=lambda e: e.ordem)],
            })
        except (KeyError, TypeError, ValueError) as e:
            db.session.rollback()
            return jsonify({'ok': False, 'erro': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'ok': False, 'erro': f'Erro ao reordenar etapas: {str(e)}'}), 500

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
        etapas = Etapa.query.join(Tarefa, Etapa.tarefa_id == Tarefa.id).join(
            Categoria, Tarefa.categoria_id == Categoria.id
        ).filter(
            Etapa.tenant_id == get_current_tenant_id(),
            Etapa.user_id == get_local_user_id(),
            Etapa.data_planejada.isnot(None),
            Tarefa.tenant_id == get_current_tenant_id(),
            Tarefa.user_id == get_local_user_id(),
            Categoria.tenant_id == get_current_tenant_id(),
            Categoria.user_id == get_local_user_id(),
        ).order_by(Etapa.data_planejada, Etapa.hora_inicio, Etapa.ordem).all()
        categorias = categorias_do_usuario()

        tarefas_json = json.dumps([{
            'id': t.id,
            'tipo': 'tarefa',
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

        etapas_json = json.dumps([{
            'id': e.id,
            'tipo': 'etapa',
            'tarefa_id': e.tarefa_id,
            'tarefa': e.titulo,
            'tarefa_principal': e.tarefa_ref.tarefa,
            'comentario': e.descricao or '',
            'data_meta': e.data_planejada.strftime('%Y-%m-%d'),
            'hora_inicio': e.hora_inicio.strftime('%H:%M') if e.hora_inicio else '',
            'hora_fim': e.hora_fim.strftime('%H:%M') if e.hora_fim else '',
            'prioridade': e.tarefa_ref.prioridade,
            'categoria_id': e.tarefa_ref.categoria_id,
            'categoria': e.tarefa_ref.categoria.nome,
            'status': e.status,
        } for e in etapas], ensure_ascii=False)

        categorias_json = json.dumps([{
            'id': c.id,
            'nome': c.nome,
            'cor': c.cor,
        } for c in categorias], ensure_ascii=False)

        return render_template(
            'calendario.html',
            tarefas_json=tarefas_json,
            etapas_json=etapas_json,
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
