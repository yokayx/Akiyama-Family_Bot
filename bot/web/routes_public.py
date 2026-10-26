"""Публичные страницы: /, /roster, /vzp, /online, /gatherings + JSON API."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bot.vzp import store

public_router = APIRouter()


def _ctx(request: Request):
    return request.app.state.ctx


def _templates(request: Request):
    return request.app.state.templates


@public_router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    ctx = _ctx(request)
    wars = await store.recent_wars(limit=5)
    stats = await store.war_stats()
    online = ctx.online
    payload = await ctx.roster.build_payload() if ctx.roster is not None else None
    return _templates(request).TemplateResponse(
        request,
        "index.html",
        {
            "title": "Akiyama Family",
            "stats": stats,
            "wars": wars,
            "roster_count": payload.unique_count if payload else 0,
            "online_count": online.online_count,
            "online_server_name": online.server_name,
            "site_url": ctx.settings.site_url,
        },
    )


@public_router.get("/roster", response_class=HTMLResponse)
async def roster(request: Request) -> HTMLResponse:
    ctx = _ctx(request)
    payload = await ctx.roster.build_payload() if ctx.roster is not None else None
    return _templates(request).TemplateResponse(
        request,
        "roster.html",
        {
            "title": "Состав · Akiyama",
            "payload": payload,
            "unique_count": payload.unique_count if payload else 0,
            "messages": list(payload.messages) if payload else [],
        },
    )


@public_router.get("/vzp", response_class=HTMLResponse)
async def vzp_page(request: Request) -> HTMLResponse:
    ctx = _ctx(request)
    wars = await store.recent_wars(limit=20)
    stats = await store.war_stats()
    top = await store.top_players(limit=10)
    return _templates(request).TemplateResponse(
        request,
        "vzp.html",
        {
            "title": "VZP · Akiyama",
            "wars": wars,
            "stats": stats,
            "top": top,
            "server_name": ctx.settings.online_server_name,
            "source_note": "vzp-launcher.pro · не официальный API GTA5RP",
        },
    )


@public_router.get("/online", response_class=HTMLResponse)
async def online_page(request: Request) -> HTMLResponse:
    ctx = _ctx(request)
    online = ctx.online
    return _templates(request).TemplateResponse(
        request,
        "online.html",
        {
            "title": "Онлайн · Akiyama",
            "online_count": online.online_count,
            "online_names": online.online_names,
            "server_name": online.server_name,
            "error": online.error,
        },
    )


@public_router.get("/gatherings", response_class=HTMLResponse)
async def gatherings_page(request: Request) -> HTMLResponse:
    ctx = _ctx(request)
    events = await ctx.plus.list_events(status="active") if ctx.plus is not None else []
    return _templates(request).TemplateResponse(
        request,
        "gatherings.html",
        {
            "title": "Сборы · Akiyama",
            "events": events,
            "moscow": "Europe/Moscow",
        },
    )


# --- JSON API -----------------------------------------------------------------


@public_router.get("/api/roster")
async def api_roster(request: Request) -> JSONResponse:
    ctx = _ctx(request)
    payload = await ctx.roster.build_payload() if ctx.roster is not None else None
    return JSONResponse(
        {
            "unique_count": payload.unique_count if payload else 0,
            "messages": list(payload.messages) if payload else [],
        }
    )


@public_router.get("/api/vzp/stats")
async def api_vzp_stats() -> JSONResponse:
    return JSONResponse(await store.war_stats())


@public_router.get("/api/vzp/wars")
async def api_vzp_wars() -> JSONResponse:
    return JSONResponse({"wars": await store.recent_wars(limit=20)})


@public_router.get("/api/vzp/top")
async def api_vzp_top() -> JSONResponse:
    return JSONResponse({"top": await store.top_players(limit=10)})


@public_router.get("/api/online")
async def api_online(request: Request) -> JSONResponse:
    ctx = _ctx(request)
    online = ctx.online
    return JSONResponse(
        {
            "server": online.server_name,
            "online": online.online_count,
            "names": online.online_names,
            "error": online.error,
        }
    )
