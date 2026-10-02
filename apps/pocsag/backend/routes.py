"""POCSAG endpoints: start / stop / status / clear.

See ``listener.py`` for the listener class, and ``src/audio/sdr_registry.py``
for why starting this can fail with a 503 while the FM listener, Pagers,
P2000, RTL433, ACARS, DAB+ or ADS-B is active (only one process can hold
the RTL-SDR dongle at a time; manual stop required by design).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import StrictBool, BaseModel, Field

from src.api.audit import AuditLogWriter
from src.api.audit.dependencies import get_audit_writer
from src.api.auth.dependencies import require_admin
from src.api.auth.jwt_session import SessionClaims

from .listener import PocsagListener


class ReceiveRequest(BaseModel):
    frequency_mhz: float = Field(ge=24, le=1766)


router = APIRouter(prefix="/api/pocsag", tags=["pocsag"])

_listener: Optional[PocsagListener] = None


def init_routes(listener: PocsagListener) -> None:
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
async def start(req: ReceiveRequest | None = None, _claims: SessionClaims = Depends(require_admin)):
    if _listener is None:
        raise HTTPException(503, "Listener not initialised")
    try:
        await _listener.start(frequency_mhz=req.frequency_mhz if req else None)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
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
    """Save plugins.pocsag.keep_running to local.yaml, merged into whatever that
    section holds on disk right now (save_section_to_yaml only merges one
    level deep, so writing {"pocsag": {"keep_running": ...}} alone would
    drop "enabled" and the plugin's other keys)."""
    import yaml

    from src.config import _get_local_yaml_path, save_section_to_yaml

    current: dict = {}
    path = _get_local_yaml_path()
    if path.exists():
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        section = data.get("plugins")
        if isinstance(section, dict) and isinstance(section.get("pocsag"), dict):
            current = dict(section["pocsag"])
    current["keep_running"] = bool(value)
    save_section_to_yaml("plugins", {"pocsag": current})


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
        params={"plugin_id": "pocsag", "keep_running": req.keep_running},
    ):
        try:
            _persist_keep_running(req.keep_running)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
    _listener.set_keep_running(req.keep_running)
    return _listener.status()
