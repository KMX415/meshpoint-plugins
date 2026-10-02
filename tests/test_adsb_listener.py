"""Tests for the ADS-B listener's lifecycle + aircraft snapshot handling.

FastAPI-free: plugins/apps/adsb/backend/listener.py imports only stdlib +
src/audio/sdr_registry.py, so it runs directly on the Mac. The dump1090
subprocess is faked with a real asyncio.StreamReader for stderr; its
/data.json webserver is faked by monkeypatching
AdsbListener._fetch_aircraft_sync directly (no real HTTP server spawned).
Mirrors plugins/apps/rtl433/backend/tests/test_listener.py.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from apps.adsb.backend import listener as adsb_listener
from apps.adsb.backend.listener import AdsbListener
from src.audio import sdr_registry


def _reader(*lines: bytes, eof: bool = True) -> asyncio.StreamReader:
    r = asyncio.StreamReader()
    for ln in lines:
        r.feed_data(ln)
    if eof:
        r.feed_eof()
    return r


_LIVE_PROCS: list = []


class _FakeProc:
    """Behaves like a real process: wait() blocks until it exits, either via
    exit() (a crash) or the patched os.killpg (a deliberate stop)."""

    def __init__(self, stderr: asyncio.StreamReader):
        self.stdout = None
        self.stderr = stderr
        self.returncode = None
        self.pid = 424242
        self._exited = asyncio.Event()
        _LIVE_PROCS.append(self)

    def exit(self, code: int = 1) -> None:
        if self.returncode is None:
            self.returncode = code
        self._exited.set()

    async def wait(self):
        await self._exited.wait()
        return self.returncode


def _fake_killpg(_pgid, sig) -> None:
    for proc in list(_LIVE_PROCS):
        proc.exit(-int(sig))
        _LIVE_PROCS.remove(proc)


_RAW_AIRCRAFT = [
    {"hex": "4b1234", "flight": "KLM123 ", "squawk": "1000", "altitude": 35000,
     "speed": 450, "track": 90, "validtrack": True, "vert_rate": 0,
     "lat": 52.3, "lon": 4.9, "validposition": True, "messages": 10, "seen": 2},
    {"hex": "4b5678", "flight": "", "squawk": "", "altitude": None,
     "speed": None, "validtrack": False, "validposition": False,
     "messages": 1, "seen": 30},
]


class TestAdsbListener(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        sdr_registry._owner = None
        _LIVE_PROCS.clear()
        self.patchers = [
            mock.patch("shutil.which", return_value="/usr/local/bin/dump1090"),
            mock.patch("os.killpg", side_effect=_fake_killpg, create=True),
            mock.patch("os.getpgid", return_value=1, create=True),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self) -> None:
        for p in self.patchers:
            p.stop()
        sdr_registry._owner = None

    async def _start(self, metric: bool = True, keep_running: bool = False) -> AdsbListener:
        lis = AdsbListener(keep_running=keep_running)
        with mock.patch("asyncio.create_subprocess_exec",
                        new=mock.AsyncMock(side_effect=lambda *a, **k: _FakeProc(_reader()))):
            with mock.patch.object(adsb_listener, "_START_CHECK_SECS", 0.02):
                await lis.start(metric=metric)
        self.assertTrue(lis.running)
        return lis

    async def test_poll_loop_parses_snapshot_and_sorts_by_seen(self) -> None:
        lis = await self._start()
        with mock.patch.object(lis, "_fetch_aircraft_sync", return_value=_RAW_AIRCRAFT):
            with mock.patch.object(adsb_listener, "_POLL_SECS", 0.01):
                lis._poll_task.cancel()
                loop = asyncio.get_running_loop()
                lis._poll_task = loop.create_task(lis._poll_loop())
                for _ in range(20):
                    await asyncio.sleep(0.01)
                    if lis.aircraft:
                        break
        # Assert before stop() -- stop() deliberately clears self.aircraft.
        self.assertEqual(len(lis.aircraft), 2)
        # Most recently heard (lowest "seen") first.
        self.assertEqual(lis.aircraft[0]["hex"], "4b1234")
        self.assertEqual(lis.aircraft[0]["flight"], "KLM123")
        self.assertEqual(lis.aircraft[0]["lat"], 52.3)
        self.assertEqual(lis.aircraft[1]["hex"], "4b5678")
        self.assertIsNone(lis.aircraft[1]["lat"])
        await lis.stop()

    async def test_failed_poll_keeps_previous_snapshot(self) -> None:
        lis = await self._start()
        with mock.patch.object(lis, "_fetch_aircraft_sync", return_value=_RAW_AIRCRAFT):
            with mock.patch.object(adsb_listener, "_POLL_SECS", 0.01):
                lis._poll_task.cancel()
                loop = asyncio.get_running_loop()
                lis._poll_task = loop.create_task(lis._poll_loop())
                for _ in range(20):
                    await asyncio.sleep(0.01)
                    if lis.aircraft:
                        break
        self.assertEqual(len(lis.aircraft), 2)
        with mock.patch.object(lis, "_fetch_aircraft_sync", return_value=None):
            with mock.patch.object(adsb_listener, "_POLL_SECS", 0.01):
                lis._poll_task.cancel()
                loop = asyncio.get_running_loop()
                lis._poll_task = loop.create_task(lis._poll_loop())
                await asyncio.sleep(0.05)
        self.assertEqual(len(lis.aircraft), 2)  # unchanged, not blanked
        await lis.stop()

    async def test_status_shape_and_metric_flag(self) -> None:
        lis = await self._start(metric=False)
        st = lis.status()
        self.assertEqual(
            set(st),
            {"running", "aircraft_count", "aircraft", "last_error",
             "metric", "keep_running", "restarts", "restarting", "dongle_owner"},
        )
        self.assertFalse(st["metric"])
        await lis.stop()

    async def test_stop_clears_aircraft(self) -> None:
        lis = await self._start()
        lis.aircraft = list(_RAW_AIRCRAFT)
        await lis.stop()
        self.assertEqual(lis.aircraft, [])
        self.assertFalse(lis.running)

    async def test_idle_stop_releases_dongle_and_clears_aircraft(self) -> None:
        """The watchdog used to cancel its own task mid-stop, leaving the
        dongle claimed by 'adsb' and the stale aircraft table in place."""
        lis = await self._start()
        lis.aircraft = list(_RAW_AIRCRAFT)
        lis._last_poll_at -= adsb_listener._IDLE_STOP_SECS + 1
        with mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            await lis._idle_watchdog()
        self.assertFalse(lis.running)
        self.assertEqual(lis.aircraft, [])
        self.assertIsNone(sdr_registry.current_owner())

    async def test_keep_running_has_no_idle_watchdog(self) -> None:
        lis = await self._start(keep_running=True)
        self.assertIsNone(lis._idle_task)
        self.assertTrue(lis.status()["keep_running"])
        await lis.stop()

    async def test_set_keep_running_applies_live(self) -> None:
        lis = await self._start()
        self.assertIsNotNone(lis._idle_task)
        lis.set_keep_running(True)
        self.assertIsNone(lis._idle_task)          # watchdog cancelled
        self.assertTrue(lis.status()["keep_running"])
        lis.set_keep_running(False)
        self.assertIsNotNone(lis._idle_task)       # watchdog back, counting from now
        await lis.stop()

    async def test_set_keep_running_while_stopped_only_sets_flag(self) -> None:
        lis = AdsbListener()
        lis.set_keep_running(True)
        self.assertTrue(lis.status()["keep_running"])
        self.assertIsNone(lis._idle_task)

    async def _wait_for(self, cond, timeout: float = 2.0) -> None:
        for _ in range(int(timeout / 0.01)):
            if cond():
                return
            await asyncio.sleep(0.01)
        self.fail("condition not reached")

    async def test_unexpected_exit_is_restarted(self) -> None:
        lis = await self._start()
        lis.aircraft = list(_RAW_AIRCRAFT)
        with mock.patch.object(adsb_listener, "_RESTART_BACKOFF_SECS", (0.01,)), \
             mock.patch.object(adsb_listener, "_START_CHECK_SECS", 0.01), \
             mock.patch("asyncio.create_subprocess_exec",
                        new=mock.AsyncMock(side_effect=lambda *a, **k: _FakeProc(_reader()))):
            crashed = lis._proc
            crashed.exit(1)
            await self._wait_for(lambda: lis.restarts == 1 and lis.running)
        self.assertIsNot(lis._proc, crashed)
        self.assertEqual(lis.aircraft, [])               # stale table dropped
        self.assertEqual(sdr_registry.current_owner(), "adsb")
        await lis.stop()
        self.assertIsNone(sdr_registry.current_owner())

    async def test_gives_up_after_repeated_exits(self) -> None:
        lis = await self._start()

        def dying_proc(*_a, **_k):
            proc = _FakeProc(_reader())
            proc.exit(1)                                  # dies straight away
            return proc

        with mock.patch.object(adsb_listener, "_RESTART_BACKOFF_SECS", (0.0,)), \
             mock.patch.object(adsb_listener, "_START_CHECK_SECS", 0.0), \
             mock.patch.object(adsb_listener, "_DEVICE_SETTLE_SECS", 0.0), \
             mock.patch("asyncio.create_subprocess_exec",
                        new=mock.AsyncMock(side_effect=dying_proc)):
            lis._proc.exit(1)
            await self._wait_for(lambda: "kept exiting" in lis._last_error)
        self.assertFalse(lis.running)
        self.assertIsNone(sdr_registry.current_owner())

    async def test_deliberate_stop_is_not_restarted(self) -> None:
        lis = await self._start()
        with mock.patch.object(adsb_listener, "_RESTART_BACKOFF_SECS", (0.0,)):
            await lis.stop()
            await asyncio.sleep(0.05)
        self.assertFalse(lis.running)
        self.assertEqual(lis.restarts, 0)
        self.assertIsNone(sdr_registry.current_owner())

    async def test_missing_binary_raises(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                await AdsbListener().start()

    async def test_stop_during_backoff_cancels_supervisor(self) -> None:
        lis = await self._start()
        with mock.patch.object(adsb_listener, "_RESTART_BACKOFF_SECS", (60,)):
            lis._proc.exit(1)
            await self._wait_for(lambda: lis._restarting)
            supervisor = lis._watch_task
            self.assertIsNotNone(supervisor)
            await lis.stop()
            await asyncio.wait_for(supervisor, 0.5)
        self.assertIsNone(sdr_registry.current_owner())
        self.assertFalse(lis._restarting)
        self.assertEqual(lis.restarts, 0)

    async def test_stable_process_resets_failure_budget(self) -> None:
        lis = await self._start()
        lis._restart_failures = 5
        with mock.patch.object(adsb_listener, "_RESTART_STABLE_SECS", 0), \
             mock.patch.object(adsb_listener, "_RESTART_BACKOFF_SECS", (60,)):
            lis._proc.exit(1)
            await self._wait_for(lambda: lis._restarting)
            self.assertEqual(lis._restart_failures, 1)
            supervisor = lis._watch_task
            await lis.stop()
            await asyncio.wait_for(supervisor, 0.5)

    async def test_dongle_owned_by_other_listener_raises(self) -> None:
        sdr_registry.claim("rtl433")
        with self.assertRaises(RuntimeError):
            await AdsbListener().start()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
