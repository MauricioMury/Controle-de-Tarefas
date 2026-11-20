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


class V5EtapasSecurityTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / 'security-v5.db'
        self.app = create_test_app(database_path)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self._seed_security_data()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _seed_security_data(self):
        tenant_a = Tenant(nome='Tenant A', slug='tenant-a')
        tenant_b = Tenant(nome='Tenant B', slug='tenant-b')
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()

        user_a = User(
            username='usuario_a',
            password=generate_password_hash('SenhaForte!123'),
            tenant_id=tenant_a.id,
        )
        user_b = User(
            username='usuario_b',
            password=generate_password_hash('SenhaForte!123'),
            tenant_id=tenant_b.id,
        )
        db.session.add_all([user_a, user_b])
        db.session.flush()

        categoria_a = Categoria(nome='Trabalho A', cor='primary', tenant_id=tenant_a.id, user_id=user_a.id)
        categoria_b = Categoria(nome='Trabalho B', cor='success', tenant_id=tenant_b.id, user_id=user_b.id)
        db.session.add_all([categoria_a, categoria_b])
        db.session.flush()

        tarefa_a = Tarefa(
            tarefa='Tarefa confidencial A',
            comentario='Nao deve aparecer para B',
            data_meta=date(2026, 7, 20),
            hora_inicio=time(9, 0),
            prioridade='Normal',
            recorrencia='Nao',
            categoria_legado=categoria_a.nome,
            categoria_id=categoria_a.id,
            status='Pendente',
            tenant_id=tenant_a.id,
            user_id=user_a.id,
        )
        tarefa_b = Tarefa(
            tarefa='Tarefa publica B',
            comentario='Controle do usuario B',
            data_meta=date(2026, 7, 21),
            hora_inicio=time(10, 0),
            prioridade='Normal',
            recorrencia='Nao',
            categoria_legado=categoria_b.nome,
            categoria_id=categoria_b.id,
            status='Pendente',
            tenant_id=tenant_b.id,
            user_id=user_b.id,
        )
        db.session.add_all([tarefa_a, tarefa_b])
        db.session.flush()

        etapa_a = Etapa(
            tarefa_id=tarefa_a.id,
            tenant_id=tenant_a.id,
            user_id=user_a.id,
            titulo='Etapa sigilosa A',
            descricao='Nao deve vazar',
            ordem=1,
            data_planejada=date(2026, 7, 20),
            status='Criada',
        )
        etapa_b = Etapa(
            tarefa_id=tarefa_b.id,
            tenant_id=tenant_b.id,
            user_id=user_b.id,
            titulo='Etapa do usuario B',
            ordem=1,
            data_planejada=date(2026, 7, 21),
            status='Criada',
        )
        db.session.add_all([etapa_a, etapa_b])
        db.session.flush()

        db.session.add(HistoricoEtapa(
            tarefa_id=tarefa_a.id,
            etapa_id=etapa_a.id,
            tenant_id=tenant_a.id,
            user_id=user_a.id,
            acao='criar',
            descricao='Historico sigiloso A',
        ))
        db.session.commit()

    def _login(self, username):
        response = self.client.post('/login', data={
            'username': username,
            'password': 'SenhaForte!123',
        })
        self.assertEqual(302, response.status_code)

    def _ids_por_usuario(self, username):
        user = User.query.filter_by(username=username).one()
        tarefa = Tarefa.query.filter_by(user_id=user.id).one()
        etapa = Etapa.query.filter_by(user_id=user.id).one()
        return tarefa.id, etapa.id

    def test_usuario_nao_lista_etapas_de_tarefa_de_outro_usuario(self):
        tarefa_a_id, _etapa_a_id = self._ids_por_usuario('usuario_a')
        self._login('usuario_b')

        response = self.client.get(f'/tarefas/{tarefa_a_id}/etapas?format=json')

        self.assertEqual(404, response.status_code)

    def test_usuario_nao_acessa_etapa_de_outro_usuario(self):
        _tarefa_a_id, etapa_a_id = self._ids_por_usuario('usuario_a')
        self._login('usuario_b')
        cenarios = [
            ('/etapas/{id}/editar?format=json', 'get'),
            ('/etapas/{id}/editar', 'post'),
            ('/etapas/{id}/iniciar', 'post'),
            ('/etapas/{id}/historico?format=json', 'get'),
            ('/etapas/{id}/deletar', 'post'),
        ]

        for path, method in cenarios:
            with self.subTest(path=path, method=method):
                if method == 'post':
                    response = self.client.post(path.format(id=etapa_a_id), json={'titulo': 'Tentativa'})
                else:
                    response = self.client.get(path.format(id=etapa_a_id))

                self.assertEqual(404, response.status_code)

    def test_usuario_nao_reordena_etapa_de_outro_usuario_em_tarefa_propria(self):
        _tarefa_a_id, etapa_a_id = self._ids_por_usuario('usuario_a')
        tarefa_b_id, _etapa_b_id = self._ids_por_usuario('usuario_b')
        self._login('usuario_b')

        response = self.client.post(
            f'/tarefas/{tarefa_b_id}/etapas/reordenar',
            json={'etapas': [{'id': etapa_a_id, 'ordem': 1}]},
        )

        self.assertEqual(400, response.status_code)
        self.assertIs(response.get_json()['ok'], False)

    def test_usuario_nao_move_tarefa_de_outro_usuario(self):
        tarefa_a_id, _etapa_a_id = self._ids_por_usuario('usuario_a')
        meta_antes = db.session.get(Tarefa, tarefa_a_id).data_meta
        self._login('usuario_b')

        for payload in ({'data_meta': '2026-12-01'}, {'data_inicio': '2026-01-01'}):
            with self.subTest(payload=payload):
                response = self.client.post(f'/mover_tarefa/{tarefa_a_id}', json=payload)
                self.assertEqual(404, response.status_code)

        db.session.expire_all()
        tarefa = db.session.get(Tarefa, tarefa_a_id)
        self.assertEqual(meta_antes, tarefa.data_meta)
        self.assertIsNone(tarefa.data_inicio)

    def test_calendario_nao_renderiza_etapas_de_outro_usuario(self):
        self._login('usuario_b')

        response = self.client.get('/calendario')

        self.assertEqual(200, response.status_code)
        body = response.get_data(as_text=True)
        self.assertIn('Etapa do usuario B', body)
        self.assertNotIn('Etapa sigilosa A', body)
        self.assertNotIn('Tarefa confidencial A', body)


if __name__ == '__main__':
    unittest.main(verbosity=2)
