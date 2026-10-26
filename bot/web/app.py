"""FastAPI-приложение: JSON API + хостинг React SPA (build из frontend/dist)."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from bot.web.context import WebContext
from bot.web.routes_public import public_router
from bot.web.routes_staff import staff_router


def create_app(ctx: WebContext, static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Akiyama Family", docs_url=None, redoc_url=None)
    app.state.ctx = ctx

    @app.exception_handler(Exception)
    async def _error_json(request: Request, exc: Exception) -> HTMLResponse:
        # SPA забирает ошибки через API; для остальных — просто 500.
        return HTMLResponse(f"<h1>500</h1><pre>{exc}</pre>", status_code=500)

    app.include_router(public_router)
    app.include_router(staff_router)

    if static_dir is not None and (static_dir / "index.html").exists():
        _mount_spa(app, static_dir)
    return app


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Вернуть статику Vite-сборки, а unknown-paths — index.html (SPA-роутинг)."""
    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def _spa(full_path: str):
        candidate = (static_dir / full_path) if full_path else None
        if candidate is not None and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")
