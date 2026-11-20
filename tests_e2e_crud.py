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
            data_inicio='2026-07-20', data_realizado='2026-07-20',
            hora_inicio='10:00', hora_fim='09:00', next=self.CALENDARIO))
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('No mesmo dia, a hora de fim deve ser posterior', html)
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


class CriadaEmTestCase(unittest.TestCase):
    """Etapa 3, Tarefa 3.1: data de criacao exibida no horario de Sao Paulo."""

    setUp = V5EtapasCrudTestCase.setUp
    tearDown = V5EtapasCrudTestCase.tearDown
    _seed_base_data = V5EtapasCrudTestCase._seed_base_data
    _login = V5EtapasCrudTestCase._login

    def _definir_criacao(self, valor):
        from datetime import datetime
        tarefa = db.session.get(Tarefa, self.tarefa_id)
        # 2026-11-20 02:30 UTC = 2026-11-19 23:30 em Sao Paulo.
        tarefa.created_at = datetime(2026, 11, 20, 2, 30) if valor else None
        db.session.commit()

    def test_filtro_converte_utc_para_sao_paulo(self):
        from datetime import datetime, timezone
        from routes.routes import formatar_data_hora_sp
        self.assertEqual('19/11/2026 23:30', formatar_data_hora_sp(datetime(2026, 11, 20, 2, 30)))
        self.assertEqual('19/11/2026 23:30', formatar_data_hora_sp(
            datetime(2026, 11, 20, 2, 30, tzinfo=timezone.utc)))
        self.assertEqual('—', formatar_data_hora_sp(None))

    def test_lista_tarefas_mostra_dia_de_sao_paulo(self):
        self._definir_criacao(True)
        self._login()
        html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertIn('Criada 19/11/2026', html)
        self.assertNotIn('Criada 20/11/2026', html)

    def test_edicao_mostra_data_e_hora_de_sao_paulo(self):
        self._definir_criacao(True)
        self._login()
        html = self.client.get(f'/editar_tarefa/{self.tarefa_id}').get_data(as_text=True)
        self.assertIn('Criada em 19/11/2026 23:30', html)

    def test_calendario_envia_criada_em(self):
        self._definir_criacao(True)
        self._login()
        html = self.client.get('/calendario').get_data(as_text=True)
        self.assertIn('"criada_em": "19/11/2026 23:30"', html)

    def test_sem_data_de_criacao_nao_quebra(self):
        self._definir_criacao(False)
        self._login()
        self.assertEqual(200, self.client.get('/lista_tarefas').status_code)
        self.assertIn('Criada em —', self.client.get(f'/editar_tarefa/{self.tarefa_id}').get_data(as_text=True))
        self.assertIn('"criada_em": ""', self.client.get('/calendario').get_data(as_text=True))

    def test_duplicar_gera_nova_data_de_criacao(self):
        self._definir_criacao(True)
        self._login()
        original = db.session.get(Tarefa, self.tarefa_id)
        self.client.post('/cadastro_tarefa', data={
            'tarefa': original.tarefa + ' copia',
            'comentario': '',
            'data_meta': '2026-07-27',
            'data_realizado': '',
            'hora_inicio': '09:00',
            'hora_fim': '',
            'prioridade': 'Normal',
            'recorrencia': 'Nao',
            'categoria_id': original.categoria_id,
            'duplicate_id': self.tarefa_id,
        })
        copia = Tarefa.query.filter(Tarefa.id != self.tarefa_id).order_by(Tarefa.id.desc()).first()
        self.assertIsNotNone(copia)
        self.assertIsNotNone(copia.created_at)
        self.assertNotEqual(original.created_at, copia.created_at)


class DataInicioTestCase(unittest.TestCase):
    """Etapa 3, Tarefa 3.2: data de inicio e horas opcionais (cada hora pertence a sua data)."""

    setUp = V5EtapasCrudTestCase.setUp
    tearDown = V5EtapasCrudTestCase.tearDown
    _seed_base_data = V5EtapasCrudTestCase._seed_base_data
    _login = V5EtapasCrudTestCase._login
    _form_tarefa = NavegacaoRetornoTestCase._form_tarefa

    def _tarefa(self, tarefa_id=None):
        db.session.expire_all()
        return db.session.get(Tarefa, tarefa_id or self.tarefa_id)

    def test_cadastro_sem_data_de_inicio_e_sem_hora(self):
        self._login()
        response = self.client.post('/cadastro_tarefa', data=self._form_tarefa(
            tarefa='Sem inicio', hora_inicio='', data_inicio=''))
        self.assertEqual(302, response.status_code)
        nova = Tarefa.query.filter_by(tarefa='Sem inicio').one()
        self.assertIsNone(nova.data_inicio)
        self.assertIsNone(nova.hora_inicio)

    def test_cadastro_com_data_e_hora_de_inicio(self):
        self._login()
        self.client.post('/cadastro_tarefa', data=self._form_tarefa(
            tarefa='Com inicio', data_inicio='2026-07-18', hora_inicio='08:15'))
        nova = Tarefa.query.filter_by(tarefa='Com inicio').one()
        self.assertEqual(date(2026, 7, 18), nova.data_inicio)
        self.assertEqual(time(8, 15), nova.hora_inicio)

    def test_inicio_depois_da_meta_e_recusado(self):
        # Mauricio: se nao comecou ate a meta, a meta deve ser adiada.
        self._login()
        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(
            data_inicio='2026-07-25'))
        self.assertEqual(200, response.status_code)
        self.assertIn('não pode ser posterior à data meta', response.get_data(as_text=True))
        self.assertIsNone(self._tarefa().data_inicio)

    def test_inicio_no_dia_da_meta_e_aceito(self):
        self._login()
        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(
            data_inicio='2026-07-20'))
        self.assertEqual(302, response.status_code)
        self.assertEqual(date(2026, 7, 20), self._tarefa().data_inicio)

    def test_arrastar_meta_para_antes_do_inicio_e_recusado(self):
        tarefa = self._tarefa()
        tarefa.data_inicio = date(2026, 7, 18)
        db.session.commit()
        self._login()
        response = self.client.post(f'/mover_tarefa/{self.tarefa_id}', json={'data_meta': '2026-07-17'})
        self.assertEqual(400, response.status_code)
        self.assertIn('antes da data de início', response.get_json()['erro'])
        self.assertEqual(date(2026, 7, 20), self._tarefa().data_meta)
        response = self.client.post(f'/mover_tarefa/{self.tarefa_id}', json={'data_meta': '2026-07-18'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(date(2026, 7, 18), self._tarefa().data_meta)

    def test_realizado_antes_do_inicio_e_recusado(self):
        self._login()
        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(
            data_inicio='2026-07-20', data_realizado='2026-07-19'))
        self.assertEqual(200, response.status_code)
        self.assertIn('não pode ser anterior à data de início', response.get_data(as_text=True))
        self.assertIsNone(self._tarefa().data_realizado)

    def test_hora_fim_menor_em_outro_dia_e_aceita(self):
        self._login()
        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(
            data_inicio='2026-07-18', hora_inicio='15:00',
            data_realizado='2026-07-20', hora_fim='10:00'))
        self.assertEqual(302, response.status_code)
        tarefa = self._tarefa()
        self.assertEqual(time(10, 0), tarefa.hora_fim)
        self.assertEqual('Concluída', tarefa.status)

    def test_hora_fim_menor_no_mesmo_dia_e_recusada(self):
        self._login()
        response = self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(
            data_inicio='2026-07-20', hora_inicio='15:00',
            data_realizado='2026-07-20', hora_fim='10:00'))
        self.assertEqual(200, response.status_code)
        self.assertIn('No mesmo dia, a hora de fim deve ser posterior', response.get_data(as_text=True))

    def test_tarefa_antiga_sem_inicio_oculta_a_hora_e_avisa(self):
        # Tarefa da base: hora 09:00 gravada quando a hora era do dia da meta.
        self._login()
        html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertIn('Sem data de início', html)
        self.assertNotIn('09:00', html)
        html = self.client.get('/calendario').get_data(as_text=True)
        self.assertIn('"data_inicio": ""', html)
        self.assertIn('"hora_inicio": ""', html)
        edicao = self.client.get(f'/editar_tarefa/{self.tarefa_id}').get_data(as_text=True)
        self.assertIn('id="aviso-sem-inicio"', edicao)
        # Na edicao a hora antiga vem preenchida para conferencia.
        self.assertIn('value="09:00"', edicao)

    def test_editar_sem_mexer_preserva_a_hora_antiga(self):
        self._login()
        self.client.post(f'/editar_tarefa/{self.tarefa_id}', data=self._form_tarefa(tarefa='Renomeada'))
        tarefa = self._tarefa()
        self.assertEqual('Renomeada', tarefa.tarefa)
        self.assertEqual(time(9, 0), tarefa.hora_inicio)
        self.assertIsNone(tarefa.data_inicio)

    def test_com_inicio_mostra_data_e_hora(self):
        tarefa = self._tarefa()
        tarefa.data_inicio = date(2026, 7, 18)
        db.session.commit()
        self._login()
        html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertIn('Início 18/07/2026 09:00', html)
        self.assertNotIn('Sem data de início', html)
        cal = self.client.get('/calendario').get_data(as_text=True)
        self.assertIn('"data_inicio": "2026-07-18"', cal)
        self.assertIn('"hora_inicio": "09:00"', cal)

    def test_concluir_usa_data_e_hora_de_sao_paulo(self):
        from datetime import datetime as dt, timezone as tz
        from unittest import mock
        import routes.routes as rotas

        self._login()
        # 2026-11-20 01:30 UTC = 2026-11-19 22:30 em Sao Paulo.
        instante_utc = dt(2026, 11, 20, 1, 30, 45, tzinfo=tz.utc)
        with mock.patch.object(rotas, 'datetime', wraps=dt) as falso:
            falso.now.side_effect = lambda fuso=None: instante_utc.astimezone(fuso)
            self.client.post(f'/marcar_concluida/{self.tarefa_id}')
        tarefa = self._tarefa()
        self.assertEqual(date(2026, 11, 19), tarefa.data_realizado)
        self.assertEqual(time(22, 30), tarefa.hora_fim)
        self.assertEqual('Concluída', tarefa.status)

    def test_concluir_preserva_hora_fim_existente(self):
        tarefa = self._tarefa()
        tarefa.hora_fim = time(17, 0)
        db.session.commit()
        self._login()
        self.client.post(f'/marcar_concluida/{self.tarefa_id}')
        self.assertEqual(time(17, 0), self._tarefa().hora_fim)

    def test_duplicar_copia_inicio_e_nao_copia_realizado(self):
        tarefa = self._tarefa()
        tarefa.data_inicio = date(2026, 7, 18)
        tarefa.data_realizado = date(2026, 7, 21)
        tarefa.hora_fim = time(18, 0)
        tarefa.status = 'Concluída'
        db.session.commit()
        self._login()
        location = self.client.get(f'/duplicar_tarefa/{self.tarefa_id}').headers['Location']
        self.assertIn('data_inicio=2026-07-18', location)
        self.assertIn('hora_inicio=09:00', location)
        self.assertNotIn('data_realizado', location)
        self.assertNotIn('hora_fim', location)
        html = self.client.get(location).get_data(as_text=True)
        self.assertIn('value="2026-07-18"', html)

    def test_ordem_no_mesmo_dia_sem_hora_por_ultimo(self):
        self._login()
        self.client.post('/cadastro_tarefa', data=self._form_tarefa(tarefa='ZZ sem hora', hora_inicio=''))
        self.client.post('/cadastro_tarefa', data=self._form_tarefa(tarefa='AA cedo', hora_inicio='07:00'))
        html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertLess(html.index('AA cedo'), html.index('Implantar novo servidor'))
        self.assertLess(html.index('Implantar novo servidor'), html.index('ZZ sem hora'))


class MigracaoDataInicioTestCase(unittest.TestCase):
    """Etapa 3, Tarefa 3.2: migracao de um banco com o DDL antigo (hora_inicio NOT NULL)."""

    DDL_TAREFA_ANTIGA = (
        'CREATE TABLE tarefa (\n'
        '    id INTEGER NOT NULL,\n'
        '    tarefa VARCHAR(200) NOT NULL,\n'
        '    comentario TEXT,\n'
        '    data_meta DATE NOT NULL,\n'
        '    data_realizado DATE,\n'
        '    hora_inicio TIME NOT NULL,\n'
        '    hora_fim TIME,\n'
        '    prioridade VARCHAR(20) NOT NULL,\n'
        '    recorrencia VARCHAR(50) NOT NULL,\n'
        '    categoria VARCHAR(50) NOT NULL,\n'
        '    categoria_id INTEGER NOT NULL,\n'
        '    status VARCHAR(20),\n'
        '    user_id INTEGER NOT NULL,\n'
        '    created_at DATETIME,\n'
        '    notif_datetime_1 DATETIME,\n'
        '    notif_email_enviada_1 BOOLEAN NOT NULL DEFAULT 0,\n'
        '    notif_datetime_2 DATETIME,\n'
        '    notif_email_enviada_2 BOOLEAN NOT NULL DEFAULT 0,\n'
        '    notif_whatsapp_enviada_1 BOOLEAN NOT NULL DEFAULT 0,\n'
        '    notif_whatsapp_enviada_2 BOOLEAN NOT NULL DEFAULT 0, tenant_id INTEGER,\n'
        '    PRIMARY KEY (id),\n'
        '    FOREIGN KEY(user_id) REFERENCES user (id),\n'
        '    FOREIGN KEY(categoria_id) REFERENCES categoria (id)\n'
        ');\n'
    )

    def setUp(self):
        import sqlite3
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / 'antigo.db')
        con = sqlite3.connect(self.db_path)
        con.executescript(
            'CREATE TABLE user (id INTEGER PRIMARY KEY, username VARCHAR(80), password VARCHAR(200));\n'
            'CREATE TABLE categoria (id INTEGER PRIMARY KEY, nome VARCHAR(50), cor VARCHAR(20), user_id INTEGER);\n'
            + self.DDL_TAREFA_ANTIGA +
            'CREATE INDEX ix_tarefa_categoria_id ON tarefa (categoria_id);\n'
            "INSERT INTO user VALUES (1, 'mauricio', 'scrypt:hash');\n"
            "INSERT INTO categoria VALUES (1, 'Trabalho', 'info', 1);\n"
            'INSERT INTO tarefa (id, tarefa, data_meta, data_realizado, hora_inicio, hora_fim, prioridade,\n'
            '                    recorrencia, categoria, categoria_id, status, user_id, created_at)\n'
            "VALUES (7, 'Antiga', '2026-05-20', '2026-05-21', '09:00:00.000000', '18:00:00.000000', 'Normal',\n"
            "        'Nao', 'Trabalho', 1, 'Concluída', 1, '2026-05-01 12:00:00');\n"
        )
        con.commit()
        con.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _info(self):
        import sqlite3
        con = sqlite3.connect(self.db_path)
        try:
            colunas = {c[1]: c[3] for c in con.execute('PRAGMA table_info(tarefa)')}
            linhas = con.execute(
                'SELECT id, tarefa, hora_inicio, hora_fim, data_inicio, tenant_id FROM tarefa'
            ).fetchall()
            indices = {
                r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='tarefa'")
            }
            etapa_fks = {r[2] for r in con.execute('PRAGMA foreign_key_list(etapa)')}
            integridade = con.execute('PRAGMA integrity_check').fetchone()[0]
            return colunas, linhas, indices, etapa_fks, integridade
        finally:
            con.close()

    def test_migracao_torna_hora_opcional_e_preserva_dados(self):
        from local_migrations import run_local_migrations
        run_local_migrations(self.db_path)
        colunas, linhas, indices, etapa_fks, integridade = self._info()
        self.assertEqual(0, colunas['hora_inicio'])
        self.assertIn('data_inicio', colunas)
        self.assertEqual(1, len(linhas))
        id_, nome, hora_inicio, hora_fim, data_inicio, tenant_id = linhas[0]
        self.assertEqual(
            (7, 'Antiga', '09:00:00.000000', '18:00:00.000000', None),
            (id_, nome, hora_inicio, hora_fim, data_inicio),
        )
        self.assertIsNotNone(tenant_id)
        self.assertIn('ix_tarefa_categoria_id', indices)
        self.assertIn('ix_tarefa_tenant_id', indices)
        self.assertIn('tarefa', etapa_fks)
        self.assertEqual('ok', integridade)

    def test_migracao_idempotente(self):
        from local_migrations import run_local_migrations
        run_local_migrations(self.db_path)
        primeira = self._info()
        run_local_migrations(self.db_path)
        self.assertEqual(primeira, self._info())

    def test_aceita_tarefa_sem_hora_depois_da_migracao(self):
        import sqlite3
        from local_migrations import run_local_migrations
        run_local_migrations(self.db_path)
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                "INSERT INTO tarefa (tarefa, data_meta, prioridade, recorrencia, categoria, categoria_id, user_id) "
                "VALUES ('Nova', '2026-12-01', 'Normal', 'Nao', 'Trabalho', 1, 1)"
            )
            con.commit()
            self.assertEqual(2, con.execute('SELECT COUNT(*) FROM tarefa').fetchone()[0])
        finally:
            con.close()


class AtrasoTestCase(unittest.TestCase):
    """Etapa 3, Tarefa 3.3: dias de atraso em relacao a meta."""

    setUp = V5EtapasCrudTestCase.setUp
    tearDown = V5EtapasCrudTestCase.tearDown
    _seed_base_data = V5EtapasCrudTestCase._seed_base_data
    _login = V5EtapasCrudTestCase._login

    def _tarefa(self):
        db.session.expire_all()
        return db.session.get(Tarefa, self.tarefa_id)

    def _concluir_em(self, realizado):
        tarefa = self._tarefa()
        tarefa.data_realizado = realizado
        tarefa.status = 'Concluída'
        db.session.commit()

    def test_dias_atraso_do_modelo(self):
        tarefa = self._tarefa()  # meta 2026-07-20, pendente
        self.assertEqual(0, tarefa.dias_atraso())
        self.assertEqual(0, tarefa.dias_atraso(date(2026, 7, 20)))
        self.assertEqual(3, tarefa.dias_atraso(date(2026, 7, 23)))
        tarefa.data_realizado = date(2026, 7, 19)
        self.assertEqual(0, tarefa.dias_atraso(date(2026, 8, 1)))
        tarefa.data_realizado = date(2026, 7, 21)
        # Concluida: conta ate a data realizado, nao ate hoje.
        self.assertEqual(1, tarefa.dias_atraso(date(2026, 8, 1)))

    def test_lista_concluida_com_atraso(self):
        self._concluir_em(date(2026, 7, 25))
        self._login()
        html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertIn('com 5 dias de atraso', html)

    def test_lista_concluida_com_um_dia_de_atraso_no_singular(self):
        self._concluir_em(date(2026, 7, 21))
        self._login()
        html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertIn('com 1 dia de atraso', html)

    def test_lista_concluida_no_prazo_sem_atraso(self):
        self._concluir_em(date(2026, 7, 20))
        self._login()
        self.assertNotIn('de atraso', self.client.get('/lista_tarefas').get_data(as_text=True))

    def test_lista_pendente_atrasada_pela_data_de_sao_paulo(self):
        from unittest import mock
        import routes.routes as rotas

        self._login()
        with mock.patch.object(rotas, 'hoje_sao_paulo', return_value=date(2026, 7, 27)):
            html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertIn('atrasada há 7 dias', html)
        with mock.patch.object(rotas, 'hoje_sao_paulo', return_value=date(2026, 7, 20)):
            html = self.client.get('/lista_tarefas').get_data(as_text=True)
        self.assertNotIn('atrasada há', html)

    def test_calendario_recebe_datas_para_calcular_o_atraso(self):
        self._concluir_em(date(2026, 7, 25))
        self._login()
        html = self.client.get('/calendario').get_data(as_text=True)
        self.assertIn('"data_meta": "2026-07-20"', html)
        self.assertIn('"data_realizado": "2026-07-25"', html)
        self.assertIn('de atraso', html)


class VerPorCalendarioTestCase(unittest.TestCase):
    """Etapa 3, Tarefa 3.4: seletor "Ver por: Meta | Inicio | Criacao" no Calendario."""

    setUp = V5EtapasCrudTestCase.setUp
    tearDown = V5EtapasCrudTestCase.tearDown
    _seed_base_data = V5EtapasCrudTestCase._seed_base_data
    _login = V5EtapasCrudTestCase._login

    def _tarefa(self):
        db.session.expire_all()
        return db.session.get(Tarefa, self.tarefa_id)

    def test_calendario_tem_o_seletor_ver_por(self):
        self._login()
        html = self.client.get('/calendario').get_data(as_text=True)
        self.assertIn('id="filtroVerPor"', html)
        for valor in ('meta', 'inicio', 'criacao'):
            self.assertIn(f'<option value="{valor}">', html)
        self.assertIn("['ver', 'filtroVerPor']", html)

    def test_data_de_criacao_no_dia_de_sao_paulo(self):
        from datetime import datetime
        tarefa = self._tarefa()
        tarefa.created_at = datetime(2026, 11, 20, 2, 30)  # 19/11 23:30 em Sao Paulo
        db.session.commit()
        self._login()
        html = self.client.get('/calendario').get_data(as_text=True)
        self.assertIn('"data_criacao": "2026-11-19"', html)

    def test_arrastar_no_modo_inicio_muda_so_a_data_de_inicio(self):
        self._login()
        response = self.client.post(f'/mover_tarefa/{self.tarefa_id}', json={'data_inicio': '2026-07-15'})
        self.assertEqual(200, response.status_code)
        tarefa = self._tarefa()
        self.assertEqual(date(2026, 7, 15), tarefa.data_inicio)
        self.assertEqual(date(2026, 7, 20), tarefa.data_meta)

    def test_arrastar_inicio_para_o_dia_da_meta_e_aceito(self):
        self._login()
        response = self.client.post(f'/mover_tarefa/{self.tarefa_id}', json={'data_inicio': '2026-07-20'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(date(2026, 7, 20), self._tarefa().data_inicio)

    def test_arrastar_inicio_para_depois_da_meta_e_recusado(self):
        self._login()
        response = self.client.post(f'/mover_tarefa/{self.tarefa_id}', json={'data_inicio': '2026-07-21'})
        self.assertEqual(400, response.status_code)
        self.assertIn('Adie a meta', response.get_json()['erro'])
        self.assertIsNone(self._tarefa().data_inicio)

    def test_arrastar_inicio_para_depois_do_realizado_e_recusado(self):
        tarefa = self._tarefa()
        tarefa.data_realizado = date(2026, 7, 18)
        tarefa.status = 'Concluída'
        db.session.commit()
        self._login()
        response = self.client.post(f'/mover_tarefa/{self.tarefa_id}', json={'data_inicio': '2026-07-19'})
        self.assertEqual(400, response.status_code)
        self.assertIn('data realizado', response.get_json()['erro'])

    def test_arrastar_inicio_com_data_invalida(self):
        self._login()
        for valor in ('', 'ontem', '2026-13-01'):
            with self.subTest(valor=valor):
                response = self.client.post(f'/mover_tarefa/{self.tarefa_id}', json={'data_inicio': valor})
                self.assertEqual(400, response.status_code)
        self.assertIsNone(self._tarefa().data_inicio)


class MigracaoTextoCorrompidoTestCase(unittest.TestCase):
    """Etapa 5, Tarefa 5.1: status e recorrencia com UTF-8 gravado duas vezes."""

    DDL_TAREFA_ANTIGA = MigracaoDataInicioTestCase.DDL_TAREFA_ANTIGA
    setUp = MigracaoDataInicioTestCase.setUp
    tearDown = MigracaoDataInicioTestCase.tearDown

    @staticmethod
    def _corromper(texto):
        return texto.encode('utf-8').decode('latin-1')

    def _inserir(self, tarefa_id, status, recorrencia, data_realizado):
        import sqlite3
        con = sqlite3.connect(self.db_path)
        con.execute(
            'INSERT INTO tarefa (id, tarefa, data_meta, data_realizado, hora_inicio, prioridade, recorrencia,'
            ' categoria, categoria_id, status, user_id)'
            " VALUES (?, 'Teste', '2026-07-11', ?, '09:00:00.000000', 'Normal', ?, 'Trabalho', 1, ?, 1)",
            (tarefa_id, data_realizado, recorrencia, status),
        )
        con.commit()
        con.close()

    def _linhas(self):
        import sqlite3
        con = sqlite3.connect(self.db_path)
        try:
            return {r[0]: r[1:] for r in con.execute('SELECT id, status, recorrencia, prioridade FROM tarefa')}
        finally:
            con.close()

    def test_desfazer_utf8_duplo(self):
        from local_migrations import _desfazer_utf8_duplo
        self.assertEqual('Concluída', _desfazer_utf8_duplo(self._corromper('Concluída')))
        self.assertEqual('DIÁRIO', _desfazer_utf8_duplo(self._corromper('DIÁRIO')))
        self.assertEqual('TERÇA', _desfazer_utf8_duplo(self._corromper(self._corromper('TERÇA'))))
        for intacto in ('Concluída', 'SÃO PAULO', 'Pendente', '', None):
            with self.subTest(intacto=intacto):
                self.assertIsNone(_desfazer_utf8_duplo(intacto))

    def test_migracao_corrige_status_e_recorrencia(self):
        from local_migrations import run_local_migrations
        self.assertEqual(b'Conclu\xc3\x83\xc2\xadda', self._corromper('Concluída').encode('utf-8'))
        self._inserir(372, self._corromper('Concluída'), self._corromper('DIÁRIO'), '2026-07-11')
        run_local_migrations(self.db_path)
        linhas = self._linhas()
        self.assertEqual(('Concluída', 'DIÁRIO', 'Normal'), linhas[372])
        self.assertEqual(('Concluída', 'Nao', 'Normal'), linhas[7])
        run_local_migrations(self.db_path)  # idempotente
        self.assertEqual(linhas, self._linhas())

    def test_status_invalido_e_recalculado_pela_data_realizado(self):
        from local_migrations import run_local_migrations
        self._inserir(20, 'xyz', 'SEXTA', '2026-07-11')
        self._inserir(21, 'xyz', 'SEXTA', None)
        self._inserir(22, None, 'SEXTA', None)
        run_local_migrations(self.db_path)
        linhas = self._linhas()
        self.assertEqual('Concluída', linhas[20][0])
        self.assertEqual('Pendente', linhas[21][0])
        self.assertEqual('Pendente', linhas[22][0])

    def test_texto_legitimo_com_til_nao_muda(self):
        from local_migrations import run_local_migrations
        self._inserir(30, 'Pendente', 'SÃO JOÃO', None)
        run_local_migrations(self.db_path)
        self.assertEqual('SÃO JOÃO', self._linhas()[30][1])


class AgoraUtcTestCase(unittest.TestCase):
    """Etapa 5, Tarefa 5.2: datetime.utcnow() (obsoleto) trocado por agora_utc()."""

    def test_agora_utc_sem_fuso_e_em_utc(self):
        from datetime import datetime, timezone
        from models import agora_utc
        valor = agora_utc()
        self.assertIsNone(valor.tzinfo)
        referencia = datetime.now(timezone.utc).replace(tzinfo=None)
        self.assertLess(abs((referencia - valor).total_seconds()), 5)

    def test_codigo_do_app_nao_usa_utcnow(self):
        raiz = Path(__file__).resolve().parent
        arquivos = ['app.py', 'models.py', 'local_migrations.py', 'notificacoes.py', 'routes/routes.py', 'routes/auth.py']
        for nome in arquivos:
            with self.subTest(arquivo=nome):
                self.assertNotIn('utcnow', (raiz / nome).read_text(encoding='utf-8-sig'))


class HoraEtapaSaoPauloTestCase(unittest.TestCase):
    """Etapa 5, Tarefa 5.3: iniciar e concluir etapa gravam a hora de Sao Paulo, e nao a de UTC."""

    setUp = V5EtapasCrudTestCase.setUp
    tearDown = V5EtapasCrudTestCase.tearDown
    _seed_base_data = V5EtapasCrudTestCase._seed_base_data
    _login = V5EtapasCrudTestCase._login

    def _criar_etapa_sem_horas(self):
        response = self.client.post(f'/tarefas/{self.tarefa_id}/etapas/nova', json={
            'titulo': 'Etapa sem horas', 'data_planejada': '2026-07-20', 'hora_inicio': '', 'hora_fim': '',
        })
        self.assertEqual(201, response.status_code)
        return response.get_json()['etapa']['id']

    def _post_em(self, url, instante_utc):
        from datetime import datetime as dt
        from unittest import mock
        import routes.routes as rotas

        with mock.patch.object(rotas, 'datetime', wraps=dt) as falso:
            falso.now.side_effect = lambda fuso=None: instante_utc.astimezone(fuso)
            response = self.client.post(url, json={})
        self.assertEqual(200, response.status_code)

    def _etapa(self, etapa_id):
        db.session.expire_all()
        return db.session.get(Etapa, etapa_id)

    def test_iniciar_e_concluir_gravam_hora_de_sao_paulo(self):
        from datetime import datetime as dt, timezone as tz
        self._login()
        etapa_id = self._criar_etapa_sem_horas()
        # 12:05:30 UTC = 09:05:30 em Sao Paulo; 20:40:10 UTC = 17:40:10.
        self._post_em(f'/etapas/{etapa_id}/iniciar', dt(2026, 11, 20, 12, 5, 30, tzinfo=tz.utc))
        self.assertEqual(time(9, 5, 30), self._etapa(etapa_id).hora_inicio)
        self._post_em(f'/etapas/{etapa_id}/concluir', dt(2026, 11, 20, 20, 40, 10, tzinfo=tz.utc))
        etapa = self._etapa(etapa_id)
        self.assertEqual(time(17, 40, 10), etapa.hora_fim)
        self.assertEqual('Concluida', etapa.status)
        self.assertIsNotNone(etapa.concluida_em)

    def test_iniciar_e_concluir_preservam_horas_informadas(self):
        from datetime import datetime as dt, timezone as tz
        self._login()
        etapa_id = V5EtapasCrudTestCase._criar_etapa(self, 'Etapa com horas')  # 09:00 a 10:00
        self._post_em(f'/etapas/{etapa_id}/iniciar', dt(2026, 11, 20, 15, 0, tzinfo=tz.utc))
        self._post_em(f'/etapas/{etapa_id}/concluir', dt(2026, 11, 20, 18, 0, tzinfo=tz.utc))
        etapa = self._etapa(etapa_id)
        self.assertEqual(time(9, 0), etapa.hora_inicio)
        self.assertEqual(time(10, 0), etapa.hora_fim)


if __name__ == '__main__':
    unittest.main(verbosity=2)
