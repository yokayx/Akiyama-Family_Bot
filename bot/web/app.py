"""FastAPI-приложение сайта (собирается create_app)."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bot.web.context import WebContext
from bot.web.routes_public import public_router
from bot.web.routes_staff import staff_router

_TEMPLATES = Path(__file__).parent / "templates"
_STATIC = Path(__file__).parent / "static"


def create_app(ctx: WebContext) -> FastAPI:
    app = FastAPI(title="Akiyama Family", docs_url=None, redoc_url=None)
    app.state.ctx = ctx
    templates = Jinja2Templates(directory=str(_TEMPLATES))
    app.state.templates = templates

    @app.exception_handler(Exception)
    async def _error_page(request: Request, exc: Exception) -> HTMLResponse:
        template = templates.get_template("error.html")
        html = template.render(
            request=request,
            title="Ошибка",
            message=str(exc) or "Неожиданная ошибка",
            site_url=ctx.settings.site_url,
        )
        return HTMLResponse(html, status_code=500)

    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
    app.include_router(public_router)
    app.include_router(staff_router)
    return app
