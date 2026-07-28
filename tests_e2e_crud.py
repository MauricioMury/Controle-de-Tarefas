from datetime import date, time
import tempfile
import unittest
from pathlib import Path

from flask import Flask
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash

from models import Categoria, Etapa, HistoricoEtapa, Tarefa, Tenant, User, db
from routes import register_auth_routes, register_routes


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


if __name__ == '__main__':
    unittest.main(verbosity=2)
