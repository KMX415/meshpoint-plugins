"""Live toggles, persisted configuration, and real auth dependencies."""
import asyncio
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.auth import dependencies
from src.api.auth.jwt_session import JwtSessionService
from src.api.audit.dependencies import get_audit_writer

NAMES = ('adsb', 'acars', 'dab', 'p2000', 'pagers', 'pocsag', 'rtl433')


def listener_for(name):
    module = importlib.import_module(f'apps.{name}.backend.listener')
    return next(v for k, v in vars(module).items()
                if k.endswith('Listener') and isinstance(v, type))()


class ToggleTests(unittest.IsolatedAsyncioTestCase):
    async def test_toggle_changes_watchdog_without_restarting_process(self):
        for name in NAMES:
            with self.subTest(plugin=name):
                listener = listener_for(name)
                self.assertFalse(listener.status()['keep_running'])
                listener.set_keep_running(True)
                self.assertIsNone(listener._proc)  # no boot/start side effect
                proc = mock.Mock(returncode=None)
                listener._proc = proc
                listener.set_keep_running(False)
                task = listener._idle_task
                self.assertIsNotNone(task)
                self.assertGreater(listener._last_poll_at, 0)
                listener.set_keep_running(False)
                self.assertIs(listener._idle_task, task)
                listener.set_keep_running(True)
                await asyncio.gather(task, return_exceptions=True)
                self.assertIsNone(listener._idle_task)
                self.assertIs(listener._proc, proc)


class RouteTests(unittest.TestCase):
    def test_auth_persistence_validation_and_failed_save(self):
        for name in NAMES:
            with self.subTest(plugin=name), tempfile.TemporaryDirectory() as tmp:
                routes = importlib.import_module(f'apps.{name}.backend.routes')
                listener = listener_for(name)
                routes.init_routes(listener)
                app = FastAPI()
                app.include_router(routes.router)
                audit = mock.MagicMock()
                app.dependency_overrides[get_audit_writer] = lambda: audit
                jwt = JwtSessionService(secret='test-secret-' * 8, expiry_minutes=10, session_version=1)
                dependencies.init_auth(jwt)
                path = Path(tmp) / 'local.yaml'
                initial = {'plugins': {name: {'enabled': True, 'device': '2'},
                                       'other': {'enabled': False}}, 'device': {'name': 'retained'}}
                path.write_text(yaml.safe_dump(initial), 'utf-8')
                with mock.patch('src.config._get_local_yaml_path', return_value=path), TestClient(app) as client:
                    url = f'/api/{name}/keep-running'
                    self.assertEqual(client.put(url, json={'keep_running': True}).status_code, 401)
                    viewer = {'Authorization': 'Bearer ' + jwt.issue('viewer', 'viewer')}
                    admin = {'Authorization': 'Bearer ' + jwt.issue('admin', 'admin')}
                    self.assertEqual(client.put(url, headers=viewer, json={'keep_running': True}).status_code, 403)
                    self.assertEqual(client.put(url, headers=admin, json={'keep_running': 'false'}).status_code, 422)
                    self.assertEqual(yaml.safe_load(path.read_text()), initial)
                    result = client.put(url, headers=admin, json={'keep_running': True})
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertTrue(listener.status()['keep_running'])
                    initial['plugins'][name]['keep_running'] = True
                    self.assertEqual(yaml.safe_load(path.read_text()), initial)
                    with mock.patch.object(routes, '_persist_keep_running', side_effect=PermissionError('denied')):
                        self.assertEqual(client.put(url, headers=admin, json={'keep_running': False}).status_code, 403)
                    self.assertTrue(listener.status()['keep_running'])
                    audit.timed_action.assert_called()
                routes.reset_routes()
                dependencies.reset_auth()
