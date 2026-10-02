"""P2000 (Dutch emergency dispatch) endpoints: start / stop / status / clear.

See ``listener.py`` for the listener class, and ``src/audio/sdr_registry.py``
for why starting this can fail with a 503 while the FM listener, Pagers,
POCSAG, RTL433, ACARS, DAB+ or ADS-B is active (only one process can hold
the RTL-SDR dongle at a time; manual stop required by design).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, StrictBool

from fastapi import APIRouter, Depends, HTTPException

from src.api.audit import AuditLogWriter
from src.api.audit.dependencies import get_audit_writer
from src.api.auth.dependencies import require_admin
from src.api.auth.jwt_session import SessionClaims

from .listener import P2000Listener

router = APIRouter(prefix="/api/p2000", tags=["p2000"])

_listener: Optional[P2000Listener] = None


def init_routes(listener: P2000Listener) -> None:
    global _listener
    _listener = listener


def reset_routes() -> None:
    global _listener
    _listener = None


@router.get("/status")
async def status():
    if _listener is None:
        raise HTTPException(503, "Listener not initialised")
    return _listener.poll()


@router.post("/start")
async def start(_claims: SessionClaims = Depends(require_admin)):
    if _listener is None:
        raise HTTPException(503, "Listener not initialised")
    try:
        await _listener.start()
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    return _listener.status()


@router.post("/stop")
async def stop(_claims: SessionClaims = Depends(require_admin)):
    if _listener is None:
        raise HTTPException(503, "Listener not initialised")
    await _listener.stop()
    return _listener.status()


@router.post("/clear")
async def clear(_claims: SessionClaims = Depends(require_admin)):
    if _listener is None:
        raise HTTPException(503, "Listener not initialised")
    _listener.clear()
    return _listener.status()


class KeepRunningRequest(BaseModel):
    keep_running: StrictBool


def _persist_keep_running(value: bool) -> None:
    """Save plugins.p2000.keep_running to local.yaml, merged into whatever that
    section holds on disk right now (save_section_to_yaml only merges one
    level deep, so writing {"p2000": {"keep_running": ...}} alone would
    drop "enabled" and the plugin's other keys)."""
    import yaml

    from src.config import _get_local_yaml_path, save_section_to_yaml

    current: dict = {}
    path = _get_local_yaml_path()
    if path.exists():
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        section = data.get("plugins")
        if isinstance(section, dict) and isinstance(section.get("p2000"), dict):
            current = dict(section["p2000"])
    current["keep_running"] = bool(value)
    save_section_to_yaml("plugins", {"p2000": current})


@router.put("/keep-running")
async def set_keep_running(
    req: KeepRunningRequest,
    _claims: SessionClaims = Depends(require_admin),
    audit: AuditLogWriter = Depends(get_audit_writer),
):
    """Toggle "keep running" (no idle auto-stop) from the tab: saved to
    local.yaml and applied to the running listener straight away."""
    if _listener is None:
        raise HTTPException(503, "Listener not initialised")
    with audit.timed_action(
        user=_claims.subject,
        action="config.plugin_update",
        params={"plugin_id": "p2000", "keep_running": req.keep_running},
    ):
        try:
            _persist_keep_running(req.keep_running)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
    _listener.set_keep_running(req.keep_running)
    return _listener.status()
