"""Receiver lifecycle regressions using fake processes, never radio hardware."""
import asyncio
import importlib
import unittest
from unittest import mock

from src.audio import sdr_registry

NAMES = ('adsb', 'acars', 'dab', 'p2000', 'pagers', 'pocsag', 'rtl433', 'radio')


class IdleShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_watchdog_can_finish_shutdown_and_release_dongle(self):
        for name in NAMES:
            with self.subTest(plugin=name):
                module = importlib.import_module(f'apps.{name}.backend.listener')
                cls = next(v for k, v in vars(module).items()
                           if k.endswith('Listener') and isinstance(v, type))
                listener = cls()
                proc = mock.Mock(returncode=None, pid=99999)
                proc.wait = mock.AsyncMock()
                listener._proc = proc
                sdr_registry._owner = name

                async def idle_stop():
                    listener._idle_task = asyncio.current_task()
                    await listener._stop_locked()

                with mock.patch.object(module.os, 'killpg', create=True), \
                     mock.patch.object(module.os, 'getpgid', return_value=1, create=True):
                    task = asyncio.create_task(idle_stop())
                    await task
                self.assertFalse(task.cancelled())
                proc.wait.assert_awaited()
                self.assertIsNone(sdr_registry.current_owner())
                self.assertIsNone(listener._proc)

    def tearDown(self):
        sdr_registry._owner = None
