from datetime import date, time
import tempfile
import threading
import unittest
from pathlib import Path

import requests
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from models import Categoria, Etapa, HistoricoEtapa, Tarefa, Tenant, User, db
from tests_e2e_crud import create_test_app


class V5EtapasVisualServerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / 'visual-v5.db'
        self.app = create_test_app(database_path)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self._seed_visual_data()

        self.server = make_server('127.0.0.1', 5050, self.app)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.session = requests.Session()

    def tearDown(self):
        self.session.close()
        self.server.shutdown()
        self.server_thread.join(timeout=5)
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def _seed_visual_data(self):
        tenant = Tenant(nome='Tenant Visual', slug='tenant-visual')
        db.session.add(tenant)
        db.session.flush()

        user = User(
            username='usuario_visual',
            password=generate_password_hash('SenhaForte!123'),
            tenant_id=tenant.id,
        )
        db.session.add(user)
        db.session.flush()

        categoria = Categoria(
            nome='Projeto',
            cor='primary',
            tenant_id=tenant.id,
            user_id=user.id,
        )
        db.session.add(categoria)
        db.session.flush()

        tarefa = Tarefa(
            tarefa='Validar V5-12 no servidor local',
            comentario='Validacao funcional e HTML renderizado',
            data_meta=date(2026, 7, 20),
            hora_inicio=time(8, 30),
            prioridade='Normal',
            recorrencia='Nao',
            categoria_legado=categoria.nome,
            categoria_id=categoria.id,
            status='Pendente',
            tenant_id=tenant.id,
            user_id=user.id,
        )
        db.session.add(tarefa)
        db.session.flush()

        etapa_1 = Etapa(
            tarefa_id=tarefa.id,
            tenant_id=tenant.id,
            user_id=user.id,
            titulo='Conferir lista de etapas',
            descricao='Etapa concluida para progresso visual',
            ordem=1,
            data_planejada=date(2026, 7, 20),
            hora_inicio=time(9, 0),
            hora_fim=time(10, 0),
            status='Concluida',
        )
        etapa_2 = Etapa(
            tarefa_id=tarefa.id,
            tenant_id=tenant.id,
            user_id=user.id,
            titulo='Conferir calendario',
            descricao='Etapa pendente para progresso visual',
            ordem=2,
            data_planejada=date(2026, 7, 20),
            hora_inicio=time(10, 0),
            hora_fim=time(11, 0),
            status='Criada',
        )
        db.session.add_all([etapa_1, etapa_2])
        db.session.flush()

        db.session.add(HistoricoEtapa(
            tarefa_id=tarefa.id,
            etapa_id=etapa_1.id,
            tenant_id=tenant.id,
            user_id=user.id,
            acao='concluir',
            descricao='Etapa concluida para validacao visual.',
        ))
        db.session.commit()

        self.tarefa_id = tarefa.id
        self.etapa_id = etapa_1.id

    def _login(self):
        response = self.session.post('http://127.0.0.1:5050/login', data={
            'username': 'usuario_visual',
            'password': 'SenhaForte!123',
        }, allow_redirects=False, timeout=5)
        self.assertEqual(302, response.status_code)

    def assert_html_ok(self, path, expected_texts):
        response = self.session.get(f'http://127.0.0.1:5050{path}', timeout=5)
        self.assertEqual(200, response.status_code)
        self.assertIn('text/html', response.headers.get('Content-Type', ''))
        html = response.text
        for text in expected_texts:
            self.assertIn(text, html)
        self.assertNotIn('Traceback', html)
        self.assertNotIn('Internal Server Error', html)
        return html

    def test_telas_v5_renderizam_no_servidor_local(self):
        self._login()

        lista_tarefas_html = self.assert_html_ok('/lista_tarefas', [
            'Validar V5-12 no servidor local',
            '1 de 2 etapas',
            'width: 50%',
            'Etapas',
        ])
        self.assertIn('bi-diagram-3', lista_tarefas_html)

        lista_etapas_html = self.assert_html_ok(f'/tarefas/{self.tarefa_id}/etapas', [
            'Etapas da Tarefa',
            'Conferir lista de etapas',
            'Conferir calendario',
            'Concluida',
            'Criada',
            'Nova Etapa',
        ])
        self.assertIn('step-summary', lista_etapas_html)

        self.assert_html_ok(f'/tarefas/{self.tarefa_id}/etapas/nova', [
            'Nova Etapa',
            'Validar V5-12 no servidor local',
        ])

        self.assert_html_ok(f'/etapas/{self.etapa_id}/editar', [
            'Conferir lista de etapas',
            'Etapa concluida para progresso visual',
        ])

        self.assert_html_ok(f'/etapas/{self.etapa_id}/historico', [
            'Historico da Etapa',
            'Etapa concluida para validacao visual.',
            'concluir',
        ])

        calendario_html = self.assert_html_ok('/calendario', [
            'Validar V5-12 no servidor local',
            'Conferir calendario',
            'Etapa',
            'Prazos de tarefas e etapas',
            'deadlineGrid',
            'renderDeadlines',
        ])
        self.assertIn('const ETAPAS =', calendario_html)
        self.assertIn('filtroTipo', calendario_html)

    def test_json_de_etapas_responde_no_servidor_local(self):
        self._login()

        response = self.session.get(
            f'http://127.0.0.1:5050/tarefas/{self.tarefa_id}/etapas?format=json',
            timeout=5,
        )

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIs(payload['ok'], True)
        self.assertEqual({'total': 2, 'concluidas': 1, 'progresso': 50}, payload['progresso'])
        self.assertEqual(2, len(payload['etapas']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
