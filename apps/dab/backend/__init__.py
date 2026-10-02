from __future__ import annotations


def register(reg) -> None:
    from .listener import DabListener
    from .routes import init_routes, router

    reg.add_router(router)
    reg.add_listener("dab", lambda: DabListener(keep_running=reg.config.get("keep_running") is True), init_routes)
