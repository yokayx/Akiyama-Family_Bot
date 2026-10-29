"""JSON API для публичных страниц (фронтенд — React SPA)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from bot.vzp import store

public_router = APIRouter()


def _ctx(request: Request):
    return request.app.state.ctx


@public_router.api_route("/api/health", methods=["GET", "HEAD"])
async def api_health() -> JSONResponse:
    """Проверка живости сайта: 200 и короткий JSON.

    Нужна мониторингу и проверке после настройки HTTPS/туннеля:
    `curl -I https://akiyama-5rp.ru/api/health`.
    """
    return JSONResponse({"ok": True, "service": "akiyama-site"})


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
            "error": online.error,
        }
    )


@public_router.get("/api/gatherings")
async def api_gatherings(request: Request) -> JSONResponse:
    ctx = _ctx(request)
    events = await ctx.plus.list_events(status="active") if ctx.plus is not None else []

    def iso(value):
        return value.isoformat() if hasattr(value, "isoformat") else None

    return JSONResponse(
        {
            "gatherings": [
                {
                    "id": e.id,
                    "title": e.title,
                    "reason": e.reason,
                    "event_time": iso(e.event_time),
                    "need_static": e.need_static,
                    "event_kind": e.event_kind,
                    "channel_id": e.channel_id,
                }
                for e in events
            ]
        }
    )
