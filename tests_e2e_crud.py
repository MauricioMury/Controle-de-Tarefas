from datetime import date, time
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

from flask import Flask
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash

from models import Categoria, Etapa, HistoricoEtapa, Tarefa, Tenant, User, db
from routes import register_auth_routes, register_routes

# Substitui app.APP_VERSION: os testes nao importam app.py (que exige .env).
APP_VERSION = 'teste'


def create_test_app(database_path):
    test_app = Flask(__name__)
    test_app.config.update(
        TESTING=True,
        SECRET_KEY='test-secret-key',
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path.as_posix()}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(test_app)
    CSRFProtect(test_app)

    login_manager = LoginManager(test_app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @test_app.context_processor
    def inject_test_context():
        return {
            'local_username': current_user.username if current_user.is_authenticated else '',
            'current_user': current_user,
            'notifications_enabled': False,
            'app_version': APP_VERSION,
        }

    register_auth_routes(test_app, lambda _usuario: None)
    register_routes(test_app)
    return test_app


class V5EtapasCrudTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / 'crud-v5.db'
        self.app = create_test_app(database_path)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self._seed_base_data()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _seed_base_data(self):
        tenant = Tenant(nome='Tenant Teste', slug='tenant-teste')
        db.session.add(tenant)
        db.session.flush()

        user = User(
            username='usuario_teste',
            password=generate_password_hash('SenhaForte!123'),
            tenant_id=tenant.id,
        )
        db.session.add(user)
        db.session.flush()

        categoria = Categoria(
            nome='Trabalho',
            cor='primary',
            tenant_id=tenant.id,
            user_id=user.id,
        )
        db.session.add(categoria)
        db.session.flush()

        tarefa = Tarefa(
            tarefa='Implantar novo servidor',
            comentario='Fluxo principal da V5',
            data_meta=date(2026, 7, 20),
            hora_inicio=time(9, 0),
            prioridade='Normal',
            recorrencia='Nao',
            categoria_legado=categoria.nome,
            categoria_id=categoria.id,
            status='Pendente',
            tenant_id=tenant.id,
            user_id=user.id,
        )
        db.session.add(tarefa)
        db.session.commit()
        self.tarefa_id = tarefa.id

    def _login(self):
        response = self.client.post('/login', data={
            'username': 'usuario_teste',
            'password': 'SenhaForte!123',
        })
        self.assertEqual(302, response.status_code)

    def _criar_etapa(self, titulo, ordem=None):
        payload = {
            'titulo': titulo,
            'descricao': f'Descricao de {titulo}',
            'data_planejada': '2026-07-20',
            'hora_inicio': '09:00',
            'hora_fim': '10:00',
        }
        if ordem is not None:
            payload['ordem'] = ordem

        response = self.client.post(f'/tarefas/{self.tarefa_id}/etapas/nova', json=payload)
        self.assertEqual(201, response.status_code)
        data = response.get_json()
        self.assertIs(data['ok'], True)
        return data['etapa']['id']

    def test_fluxo_principal_de_etapas_com_progresso_e_historico(self):
        self._login()

        response = self.client.get(f'/tarefas/{self.tarefa_id}/etapas/nova?format=json')
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.get_json()['proxima_ordem'])

        etapa_1_id = self._criar_etapa('Preparar servidor', ordem=1)
        etapa_2_id = self._criar_etapa('Validar funcionamento', ordem=2)

        response = self.client.get(f'/tarefas/{self.tarefa_id}/etapas?format=json')
        self.assertEqual(200, response.status_code)
        progresso = response.get_json()['progresso']
        self.assertEqual({'total': 2, 'concluidas': 0, 'progresso': 0}, progresso)

        response = self.client.post(f'/etapas/{etapa_1_id}/editar', json={
            'titulo': 'Preparar servidor atualizado',
            'descricao': 'Descricao atualizada',
            'data_planejada': '2026-07-21',
            'hora_inicio': '10:00',
            'hora_fim': '11:00',
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual('Preparar servidor atualizado', response.get_json()['etapa']['titulo'])

        for endpoint, status_esperado in [
            ('iniciar', 'Iniciada'),
            ('pausar', 'Pausada'),
            ('retomar', 'Iniciada'),
            ('concluir', 'Concluida'),
        ]:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(f'/etapas/{etapa_1_id}/{endpoint}', json={})
                self.assertEqual(200, response.status_code)
                self.assertEqual(status_esperado, response.get_json()['etapa']['status'])

        response = self.client.post(f'/etapas/{etapa_1_id}/iniciar', json={})
        self.assertEqual(400, response.status_code)
        self.assertIn('Transi', response.get_json()['erro'])

        response = self.client.get(f'/tarefas/{self.tarefa_id}/etapas?format=json')
        self.assertEqual(200, response.status_code)
        self.assertEqual({'total': 2, 'concluidas': 1, 'progresso': 50}, response.get_json()['progresso'])

        response = self.client.get(f'/etapas/{etapa_1_id}/historico?format=json')
        self.assertEqual(200, response.status_code)
        acoes = [item['acao'] for item in response.get_json()['historico']]
        for acao in ['criar', 'editar', 'iniciar', 'pausar', 'retomar', 'concluir']:
            self.assertIn(acao, acoes)

        response = self.client.get('/lista_tarefas')
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('1 de 2 etapas', html)
        self.assertIn('width: 50%', html)

        response = self.client.get(f'/tarefas/{self.tarefa_id}/etapas')
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('Preparar servidor atualizado', html)
        self.assertIn('Concluida', html)

        response = self.client.post(
            f'/tarefas/{self.tarefa_id}/etapas/reordenar',
            json={'etapas': [
                {'id': etapa_1_id, 'ordem': 2},
                {'id': etapa_2_id, 'ordem': 1},
            ]},
        )
        self.assertEqual(200, response.status_code)
        etapas = response.get_json()['etapas']
        self.assertEqual([etapa_2_id, etapa_1_id], [item['id'] for item in etapas])
        self.assertEqual([1, 2], [item['ordem'] for item in etapas])

        self.assertEqual(2, Etapa.query.count())
        self.assertGreaterEqual(HistoricoEtapa.query.count(), 8)

    def test_duplicar_tarefa_copia_etapas_com_status_criada(self):
        self._login()

        etapa_1_id = self._criar_etapa('Preparar checklist', ordem=1)
        etapa_2_id = self._criar_etapa('Executar validacao', ordem=2)

        self.client.post(f'/etapas/{etapa_1_id}/iniciar', json={})
        self.client.post(f'/etapas/{etapa_1_id}/concluir', json={})

        categoria = Categoria.query.first()
        response = self.client.post('/cadastro_tarefa', data={
            'duplicate_id': self.tarefa_id,
            'tarefa': 'Implantar novo servidor - copia',
            'comentario': 'Copia com etapas',
            'data_meta': '2026-07-22',
            'data_realizado': '',
            'hora_inicio': '13:00',
            'hora_fim': '',
            'prioridade': 'Normal',
            'recorrencia': 'ESPORÁDICO',
            'categoria_id': categoria.id,
        })
        self.assertEqual(302, response.status_code)

        db.session.expire_all()
        tarefa_copiada = Tarefa.query.filter_by(tarefa='Implantar novo servidor - copia').one()
        etapas_copiadas = Etapa.query.filter_by(tarefa_id=tarefa_copiada.id).order_by(Etapa.ordem).all()

        self.assertEqual(2, len(etapas_copiadas))
        self.assertEqual(
            ['Preparar checklist', 'Executar validacao'],
            [etapa.titulo for etapa in etapas_copiadas],
        )
        self.assertEqual([1, 2], [etapa.ordem for etapa in etapas_copiadas])
        self.assertEqual([date(2026, 7, 22), date(2026, 7, 22)], [etapa.data_planejada for etapa in etapas_copiadas])
        self.assertEqual(['Criada', 'Criada'], [etapa.status for etapa in etapas_copiadas])
        self.assertTrue(all(etapa.concluida_em is None for etapa in etapas_copiadas))
        self.assertNotIn(etapa_1_id, [etapa.id for etapa in etapas_copiadas])
        self.assertNotIn(etapa_2_id, [etapa.id for etapa in etapas_copiadas])

        historicos_copiados = HistoricoEtapa.query.filter_by(tarefa_id=tarefa_copiada.id).all()
        self.assertEqual(2, len(historicos_copiados))
        self.assertEqual({'criar'}, {historico.acao for historico in historicos_copiados})

    def test_validacoes_de_criacao_e_status(self):
        self._login()

        response = self.client.post('/cadastro_tarefa', data={
            'tarefa': 'Tarefa sem categoria',
            'comentario': '',
            'data_meta': '2026-07-22',
            'data_realizado': '',
            'hora_inicio': '',
            'hora_fim': '',
            'prioridade': 'Normal',
            'recorrencia': 'ESPORÃDICO',
            'categoria_id': '999999',
        })
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('/lista_tarefas?categoria=', html)
        self.assertIn('Cadastrar Nova Tarefa', html)

        response = self.client.post(f'/tarefas/{self.tarefa_id}/etapas/nova', json={
            'titulo': '   ',
            'data_planejada': '2026-07-20',
        })
        self.assertEqual(400, response.status_code)
        self.assertIn('t', response.get_json()['erro'].lower())

        response = self.client.post(f'/tarefas/{self.tarefa_id}/etapas/nova', json={
            'titulo': 'Horario invalido',
            'hora_inicio': '10:00',
            'hora_fim': '09:00',
        })
        self.assertEqual(400, response.status_code)
        self.assertIn('hora de fim', response.get_json()['erro'])

        etapa_id = self._criar_etapa('Etapa com transicao invalida')
        response = self.client.post(f'/etapas/{etapa_id}/concluir', json={})
        self.assertEqual(400, response.status_code)
        self.assertIn('Transi', response.get_json()['erro'])

    def test_editar_tarefa_altera_prioridade(self):
        self._login()
        categoria = Categoria.query.first()

        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data={
            'tarefa': 'Implantar novo servidor',
            'comentario': 'Prioridade alterada',
            'data_meta': '2026-07-20',
            'data_realizado': '',
            'hora_inicio': '09:00',
            'hora_fim': '',
            'prioridade': 'Muito Importante',
            'recorrencia': 'ESPORÁDICO',
            'categoria_id': categoria.id,
        })
        self.assertEqual(302, response.status_code)

        db.session.expire_all()
        tarefa = db.session.get(Tarefa, self.tarefa_id)
        self.assertEqual('Muito Importante', tarefa.prioridade)

    def test_renderizacao_html_das_telas_de_etapa(self):
        self._login()
        etapa_id = self._criar_etapa('Etapa renderizada')

        for path, texto_esperado in [
            (f'/tarefas/{self.tarefa_id}/etapas', 'Etapa renderizada'),
            (f'/tarefas/{self.tarefa_id}/etapas/nova', 'Nova Etapa'),
            (f'/etapas/{etapa_id}/editar', 'Etapa renderizada'),
            (f'/etapas/{etapa_id}/historico', 'Etapa criada.'),
            (f'/editar_tarefa/{self.tarefa_id}', '0 de 1 etapas'),
        ]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(200, response.status_code)
                self.assertIn(texto_esperado, response.get_data(as_text=True))

        response = self.client.get(f'/tarefas/{self.tarefa_id}/etapas')
        html = response.get_data(as_text=True)
        self.assertIn('Aplicar ordem da etapa', html)
        self.assertIn('Subir etapa', html)
        self.assertIn('Descer etapa', html)


class NavegacaoRetornoTestCase(unittest.TestCase):
    """Etapa 2: voltar para a tela de origem (parametro next)."""

    # Reaproveita banco, usuario, tarefa e helpers do caso V5 sem herdar os testes dele.
    setUp = V5EtapasCrudTestCase.setUp
    tearDown = V5EtapasCrudTestCase.tearDown
    _seed_base_data = V5EtapasCrudTestCase._seed_base_data
    _login = V5EtapasCrudTestCase._login
    _criar_etapa = V5EtapasCrudTestCase._criar_etapa

    CALENDARIO = '/calendario?status=Pendente&mes=2026-07&dia=2026-07-20'

    def _form_tarefa(self, **extra):
        dados = {
            'tarefa': 'Implantar novo servidor',
            'comentario': '',
            'data_meta': '2026-07-20',
            'data_realizado': '',
            'hora_inicio': '09:00',
            'hora_fim': '',
            'prioridade': 'Normal',
            'recorrencia': 'Nao',
            'categoria_id': Categoria.query.first().id,
        }
        dados.update(extra)
        return dados

    def _location(self, response):
        self.assertEqual(302, response.status_code)
        return response.headers['Location']

    def test_url_retorno_segura_aceita_so_caminhos_internos(self):
        from routes.routes import url_retorno_segura

        self.assertEqual(self.CALENDARIO, url_retorno_segura(self.CALENDARIO))
        for valor in ('https://exemplo.com', '//exemplo.com', '/\\exemplo.com', 'javascript:alert(1)',
                      'calendario', '/calendario\r\nSet-Cookie: x=1', '', None, '/' + 'a' * 3000):
            with self.subTest(valor=valor):
                self.assertIsNone(url_retorno_segura(valor))

    def test_editar_volta_para_o_calendario_com_filtros(self):
        self._login()
        html = self.client.get(f'/editar_tarefa/{self.tarefa_id}?next={quote(self.CALENDARIO)}').get_data(as_text=True)
        self.assertIn('name="next"', html)

        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(next=self.CALENDARIO))
        self.assertEqual(self.CALENDARIO, self._location(response))

    def test_next_externo_e_ignorado(self):
        self._login()
        for externo in ('https://exemplo.com/', '//exemplo.com/'):
            with self.subTest(next=externo):
                response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(next=externo))
                location = self._location(response)
                self.assertTrue(location.startswith('/lista_tarefas'), location)

    def test_sem_next_mantem_retorno_para_minhas_tarefas(self):
        self._login()
        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa())
        self.assertTrue(self._location(response).startswith('/lista_tarefas'))

    def test_duplicar_pelo_calendario_volta_para_o_calendario(self):
        self._login()
        location = self._location(self.client.get(f'/duplicar_tarefa/{self.tarefa_id}?next={quote(self.CALENDARIO)}'))
        self.assertIn('next=', location)

        # Abrir o cadastro com os dados da duplicacao nao vira filtro de Minhas Tarefas.
        html = self.client.get(location).get_data(as_text=True)
        self.assertIn('name="next"', html)
        with self.client.session_transaction() as sessao:
            self.assertFalse(sessao.get('filtro_prioridade'))

        response = self.client.post('/cadastro_tarefa', data=self._form_tarefa(
            data_meta='2026-07-27', duplicate_id=self.tarefa_id, next=self.CALENDARIO))
        self.assertEqual(self.CALENDARIO, self._location(response))
        self.assertEqual(2, Tarefa.query.count())

    def test_concluir_e_deletar_pelo_calendario_voltam_para_o_calendario(self):
        self._login()
        response = self.client.post(f'/marcar_concluida/{self.tarefa_id}', data={'next': self.CALENDARIO})
        self.assertEqual(self.CALENDARIO, self._location(response))

        response = self.client.post(f'/deletar_tarefa/{self.tarefa_id}', data={'next': self.CALENDARIO})
        self.assertEqual(self.CALENDARIO, self._location(response))
        self.assertEqual(0, Tarefa.query.count())

    def test_editar_etapa_pelo_calendario_volta_para_o_calendario(self):
        self._login()
        etapa_id = self._criar_etapa('Etapa do calendario')
        html = self.client.get(f'/etapas/{etapa_id}/editar?next={quote(self.CALENDARIO)}').get_data(as_text=True)
        self.assertIn('name="next"', html)

        response = self.client.post(f'/etapas/{etapa_id}/editar', data={
            'titulo': 'Etapa editada', 'descricao': '', 'data_planejada': '2026-07-21',
            'hora_inicio': '', 'hora_fim': '', 'next': self.CALENDARIO,
        })
        self.assertEqual(self.CALENDARIO, self._location(response))

    def test_lista_de_etapas_aberta_pelo_calendario_tem_botao_voltar(self):
        self._login()
        html = self.client.get(f'/tarefas/{self.tarefa_id}/etapas?next={quote(self.CALENDARIO)}').get_data(as_text=True)
        self.assertIn('href="/calendario?status=Pendente&amp;mes=2026-07&amp;dia=2026-07-20"', html)

    def test_erro_de_validacao_na_edicao_renderiza_a_tela(self):
        self._login()
        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(
            hora_inicio='10:00', hora_fim='09:00', next=self.CALENDARIO))
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('A hora de fim deve ser posterior', html)
        self.assertIn('name="next"', html)


class ListaTarefasPaginacaoTestCase(unittest.TestCase):
    """Etapa 1 do roadmap: itens por pagina em Minhas Tarefas."""

    TOTAL_TAREFAS = 25

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / 'paginacao.db'
        self.app = create_test_app(database_path)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self._seed()
        self.client = self.app.test_client()
        response = self.client.post('/login', data={
            'username': 'usuario_paginacao',
            'password': 'SenhaForte!123',
        })
        self.assertEqual(302, response.status_code)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _seed(self):
        tenant = Tenant(nome='Tenant Paginacao', slug='tenant-paginacao')
        db.session.add(tenant)
        db.session.flush()
        user = User(
            username='usuario_paginacao',
            password=generate_password_hash('SenhaForte!123'),
            tenant_id=tenant.id,
        )
        db.session.add(user)
        db.session.flush()
        categoria = Categoria(nome='Casa', cor='warning', tenant_id=tenant.id, user_id=user.id)
        db.session.add(categoria)
        db.session.flush()

        # Datas crescentes: a tarefa N fica na posicao N da lista ordenada.
        for numero in range(1, self.TOTAL_TAREFAS + 1):
            db.session.add(Tarefa(
                tarefa=f'Paginada {numero:02d}',
                data_meta=date(2026, 8, numero),
                hora_inicio=time(9, 0),
                prioridade='Normal',
                recorrencia='Nao',
                categoria_legado=categoria.nome,
                categoria_id=categoria.id,
                status='Pendente' if numero % 2 else 'Concluída',
                tenant_id=tenant.id,
                user_id=user.id,
            ))
        db.session.commit()

    def _html(self, query_string):
        response = self.client.get(f'/lista_tarefas?{query_string}')
        self.assertEqual(200, response.status_code)
        return response.get_data(as_text=True)

    def test_trocar_itens_por_pagina_volta_para_primeira_pagina(self):
        html = self._html('page=3&per_page=10')
        self.assertIn('Paginada 21', html)
        self.assertNotIn('Paginada 01', html)

        # O formulario "Itens por pagina" nao envia page.
        html = self._html('per_page=100')
        for numero in (1, 13, 25):
            self.assertIn(f'Paginada {numero:02d}', html)

    def test_aplicar_filtro_volta_para_primeira_pagina(self):
        self._html('page=3&per_page=5')

        # Pendentes sao as impares: 13 tarefas, a primeira pagina comeca na 01.
        html = self._html('status=Pendente&per_page=5')
        self.assertIn('Paginada 01', html)
        self.assertIn('Paginada 09', html)
        self.assertNotIn('Paginada 11', html)

    def test_pagina_alem_do_total_mostra_a_ultima(self):
        html = self._html('page=99&per_page=10')
        self.assertIn('Paginada 25', html)
        self.assertNotIn('Paginada 20', html)

    def test_itens_por_pagina_invalido_usa_padrao(self):
        for valor in ('0', '-5', '7', 'abc', '100000'):
            with self.subTest(per_page=valor):
                html = self._html(f'page=1&per_page={valor}')
                self.assertIn('Paginada 10', html)
                self.assertNotIn('Paginada 11', html)

    def test_pagina_mantida_ao_navegar_sem_parametros(self):
        self._html('page=2&per_page=10')
        html = self._html('')
        self.assertIn('Paginada 11', html)
        self.assertNotIn('Paginada 10', html)

    def test_lista_vazia_nao_quebra(self):
        html = self._html('busca=inexistente&per_page=10')
        self.assertIn('Total: 0 tarefas', html)


class DashboardIndicadoresTestCase(unittest.TestCase):
    """Etapa 1, tarefa 1.2: Inicio independente dos filtros de Minhas Tarefas."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / 'dashboard.db'
        self.app = create_test_app(database_path)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self._seed()
        self.client = self.app.test_client()
        response = self.client.post('/login', data={
            'username': 'usuario_dashboard',
            'password': 'SenhaForte!123',
        })
        self.assertEqual(302, response.status_code)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _criar_usuario(self, slug):
        tenant = Tenant(nome=f'Tenant {slug}', slug=slug)
        db.session.add(tenant)
        db.session.flush()
        user = User(
            username=f'usuario_{slug}',
            password=generate_password_hash('SenhaForte!123'),
            tenant_id=tenant.id,
        )
        db.session.add(user)
        db.session.flush()
        return tenant, user

    def _criar_categoria(self, tenant, user, nome):
        categoria = Categoria(nome=nome, cor='info', tenant_id=tenant.id, user_id=user.id)
        db.session.add(categoria)
        db.session.flush()
        return categoria

    def _criar_tarefa(self, tenant, user, categoria, status, prioridade='Normal', data_meta=date(2026, 1, 10)):
        db.session.add(Tarefa(
            tarefa=f'{categoria.nome} {status} {prioridade}',
            data_meta=data_meta,
            hora_inicio=time(9, 0),
            prioridade=prioridade,
            recorrencia='Nao',
            categoria_legado=categoria.nome,
            categoria_id=categoria.id,
            status=status,
            tenant_id=tenant.id,
            user_id=user.id,
        ))

    def _seed(self):
        from routes.routes import hoje_sao_paulo

        tenant, user = self._criar_usuario('dashboard')
        trabalho = self._criar_categoria(tenant, user, 'Trabalho')
        casa = self._criar_categoria(tenant, user, 'Casa')

        # 6 tarefas: 4 pendentes, 2 concluidas, 2 muito importantes, 1 com meta hoje.
        self._criar_tarefa(tenant, user, trabalho, 'Pendente', 'Muito Importante')
        self._criar_tarefa(tenant, user, trabalho, 'Pendente', data_meta=hoje_sao_paulo())
        self._criar_tarefa(tenant, user, trabalho, 'Concluída')
        self._criar_tarefa(tenant, user, casa, 'Pendente')
        self._criar_tarefa(tenant, user, casa, 'Pendente', 'Muito Importante')
        self._criar_tarefa(tenant, user, casa, 'Concluída')

        # Tarefas de outro usuario nao entram nos indicadores.
        outro_tenant, outro_user = self._criar_usuario('outro')
        outra_categoria = self._criar_categoria(outro_tenant, outro_user, 'Trabalho')
        for _ in range(3):
            self._criar_tarefa(outro_tenant, outro_user, outra_categoria, 'Pendente', 'Muito Importante',
                               data_meta=hoje_sao_paulo())
        db.session.commit()

    def _indicadores(self):
        response = self.client.get('/')
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        valores = {}
        for chave in ('total', 'pendente', 'concluida', 'importante', 'hoje'):
            match = re.search(rf'id="stat-{chave}">\s*(\d+)\s*<', html)
            self.assertIsNotNone(match, f'indicador stat-{chave} ausente')
            valores[chave] = int(match.group(1))
        return valores, html

    def test_indicadores_contam_todas_as_tarefas_do_usuario(self):
        valores, html = self._indicadores()
        self.assertEqual(
            {'total': 6, 'pendente': 4, 'concluida': 2, 'importante': 2, 'hoje': 1},
            valores,
        )
        # Nao busca mais /lista_tarefas em segundo plano.
        self.assertNotIn('fetch(', html)

    def test_filtros_de_minhas_tarefas_nao_afetam_o_inicio(self):
        self.client.get('/lista_tarefas?categoria=Casa&status=Concluída&prioridade=Normal&per_page=5')
        valores, _html = self._indicadores()
        self.assertEqual(6, valores['total'])
        self.assertEqual(4, valores['pendente'])

    def test_inicio_nao_altera_os_filtros_de_minhas_tarefas(self):
        self.client.get('/lista_tarefas?categoria=Casa&status=Pendente&per_page=20&page=1')
        with self.client.session_transaction() as sessao:
            antes = {k: v for k, v in sessao.items() if k.startswith('filtro_')}

        self._indicadores()

        with self.client.session_transaction() as sessao:
            depois = {k: v for k, v in sessao.items() if k.startswith('filtro_')}
        self.assertEqual(antes, depois)
        self.assertEqual('Casa', depois['filtro_categoria'])

    def test_hoje_usa_data_de_sao_paulo(self):
        from datetime import datetime as dt, timezone as tz
        from unittest import mock

        import routes.routes as rotas

        # 2026-11-20 01:30 UTC = 2026-11-19 22:30 em Sao Paulo.
        instante_utc = dt(2026, 11, 20, 1, 30, tzinfo=tz.utc)
        with mock.patch.object(rotas, 'datetime', wraps=dt) as falso:
            falso.now.side_effect = lambda fuso=None: instante_utc.astimezone(fuso)
            self.assertEqual(date(2026, 11, 19), rotas.hoje_sao_paulo())


if __name__ == '__main__':
    unittest.main(verbosity=2)
