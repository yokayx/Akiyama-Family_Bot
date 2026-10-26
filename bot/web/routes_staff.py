"""Панель стаффа: Discord OAuth + JSON API (фронтенд — React SPA)."""
from __future__ import annotations

import json
import secrets as py_secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from bot.config import (
    GUILD_ID,
    LEADERSHIP_ROLE_IDS,
    MOSCOW_TZ,
    PLUS_DEF_CHANNEL_ID,
    PLUS_KIND_LABELS,
    PLUS_KIND_PINGS,
    STAFF_ROLE_IDS,
)
from bot.web.oauth import build_authorize_url, exchange_code, fetch_guild_member, fetch_oauth_user
from bot.web.session import SESSION_COOKIE, SESSION_TTL_SECONDS, create_session, read_session

staff_router = APIRouter()

_STAFF_ROLE_IDS = set(STAFF_ROLE_IDS) | set(LEADERSHIP_ROLE_IDS)


def _ctx(request: Request):
    return request.app.state.ctx


def _current_user(request: Request) -> dict | None:
    ctx = _ctx(request)
    return read_session(request.cookies.get(SESSION_COOKIE), ctx.secret)


def _require_staff(request: Request) -> dict:
    user = _current_user(request)
    if user is None or not user.get("is_staff"):
        raise HTTPException(status_code=401, detail="Требуется вход как стафф")
    return user


def _error_json(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status_code)


# --- OAuth --------------------------------------------------------------------


@staff_router.get("/auth/callback")
async def auth_callback(request: Request, code: str = "", state: str = ""):
    ctx = _ctx(request)
    settings = ctx.settings
    if state != getattr(request.app.state, "oauth_state", None):
        return _error_json(400, "Запрос неизвестен — вернитесь к входу.")
    if not code:
        return _error_json(400, "OAuth вернул пустой code.")
    token = await exchange_code(
        client_id=settings.oauth_client_id,
        client_secret=settings.oauth_client_secret,
        code=code,
        redirect_uri=settings.oauth_redirect_uri,
    )
    user = await fetch_oauth_user(token["access_token"])
    member = await fetch_guild_member(token["access_token"], GUILD_ID)
    if member is None:
        return _error_json(403, "Аккаунт не найден на сервере family.")
    role_ids = {role["id"] for role in member.get("roles", [])}
    if not role_ids & _STAFF_ROLE_IDS:
        return _error_json(403, "Нет staff-роли на сервере.")
    cookie = create_session(
        uid=user["id"],
        name=user.get("username", ""),
        is_staff=True,
        secret=ctx.secret,
        ttl=SESSION_TTL_SECONDS,
    )
    response = RedirectResponse("/staff", status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        cookie,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return response


@staff_router.get("/api/me")
async def api_me(request: Request):
    user = _current_user(request)
    if user is None or not user.get("is_staff"):
        raise HTTPException(status_code=401, detail="Требуется вход как стафф")
    return {"uid": user["uid"], "name": user.get("name", ""), "is_staff": True}


@staff_router.get("/api/staff/login-url")
async def api_login_url(request: Request):
    ctx = _ctx(request)
    settings = ctx.settings
    if not settings.oauth_client_id or not settings.oauth_client_secret:
        return _error_json(500, "OAuth не настроен (.env: OAUTH_CLIENT_ID/SECRET)")
    state = py_secrets.token_urlsafe(24)
    request.app.state.oauth_state = state
    url = build_authorize_url(
        client_id=settings.oauth_client_id,
        redirect_uri=settings.oauth_redirect_uri,
        state=state,
    )
    return {"url": url}


@staff_router.post("/api/staff/logout")
async def api_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE)
    return response


@staff_router.post("/auth/logout")
async def logout_redirect():
    response = RedirectResponse("/staff/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


# --- Заявки --------------------------------------------------------------------


def _ticket_json(ticket, answers: list[dict], applicant_label: str, handler_label: str) -> dict:
    def iso(value):
        return value.isoformat() if isinstance(value, datetime) else None

    return {
        "id": ticket.id,
        "channel_id": ticket.channel_id,
        "applicant_id": ticket.applicant_id,
        "kind": ticket.kind,
        "handler_id": ticket.handler_id,
        "status": ticket.status,
        "answers": answers,
        "applicant_replied": ticket.applicant_replied,
        "rejection_reason": ticket.rejection_reason,
        "created_at": iso(ticket.created_at),
        "claimed_at": iso(ticket.claimed_at),
        "closed_at": iso(ticket.closed_at),
        "applicant_label": applicant_label,
        "handler_label": handler_label,
    }


@staff_router.get("/api/staff/tickets")
async def api_staff_tickets(request: Request, status: str = "open", kind: str = ""):
    _require_staff(request)
    ctx = _ctx(request)
    if not (applications_cog := ctx.applications):
        return {"tickets": []}
    if status == "all":
        tickets = await applications_cog.list_tickets(kind=kind or None)
    else:
        tickets = await applications_cog.list_tickets(statuses=(status,), kind=kind or None)
    guild = ctx.guild

    def brief(ticket):
        member = guild.get_member(ticket.applicant_id) if guild else None
        label = member.display_name if member is not None else f"user:{ticket.applicant_id}"
        return {
            "id": ticket.id,
            "channel_id": ticket.channel_id,
            "kind": ticket.kind,
            "status": ticket.status,
            "handler_id": ticket.handler_id,
            "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
            "applicant_label": label,
        }

    return {"tickets": [brief(t) for t in tickets]}


@staff_router.get("/api/staff/tickets/{ticket_id}")
async def api_staff_ticket(request: Request, ticket_id: int):
    _require_staff(request)
    ctx = _ctx(request)
    ticket = await ctx.applications.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    try:
        answers = json.loads(ticket.answers_json)
    except json.JSONDecodeError:
        answers = []
    guild = ctx.guild
    applicant_member = guild.get_member(ticket.applicant_id) if guild else None
    if applicant_member is not None:
        applicant_label = applicant_member.display_name
    else:
        applicant_label = f"user:{ticket.applicant_id}"
    handler_member = guild.get_member(ticket.handler_id) if guild and ticket.handler_id else None
    handler_label = handler_member.display_name if handler_member is not None else "—"
    return _ticket_json(ticket, answers, applicant_label, handler_label)


@staff_router.post("/api/staff/tickets/{ticket_id}/claim")
async def api_claim(request: Request, ticket_id: int):
    user = _require_staff(request)
    ctx = _ctx(request)
    ok, message = await ctx.applications.claim_ticket(ticket_id, user["uid"], f"@{user['name']}")
    return JSONResponse({"ok": ok, "message": message})


@staff_router.post("/api/staff/tickets/{ticket_id}/release")
async def api_release(request: Request, ticket_id: int):
    _require_staff(request)
    ctx = _ctx(request)
    ok, message = await ctx.applications.release_ticket(ticket_id)
    return JSONResponse({"ok": ok, "message": message})


@staff_router.post("/api/staff/tickets/{ticket_id}/accept")
async def api_accept(request: Request, ticket_id: int):
    _require_staff(request)
    ctx = _ctx(request)
    guild = ctx.guild
    if guild is None:
        return _error_json(500, "Бот не на сервере")
    ok, message = await ctx.applications.accept_ticket(ticket_id, guild)
    return JSONResponse({"ok": ok, "message": message})


@staff_router.post("/api/staff/tickets/{ticket_id}/reject")
async def api_reject(request: Request, ticket_id: int, reason: str = Form("")):
    _require_staff(request)
    ctx = _ctx(request)
    guild = ctx.guild
    if guild is None:
        return _error_json(500, "Бот не на сервере")
    reason_text = reason.strip() or "(без причины)"
    ok, message = await ctx.applications.reject_ticket(ticket_id, reason_text, guild)
    return JSONResponse({"ok": ok, "message": message})


# --- Сборы ---------------------------------------------------------------------


def _event_json(event) -> dict:
    return {
        "id": event.id,
        "channel_id": event.channel_id,
        "creator_id": event.creator_id,
        "title": event.title,
        "reason": event.reason,
        "event_time": event.event_time.isoformat() if event.event_time else None,
        "need_static": event.need_static,
        "is_active": event.is_active,
        "event_kind": event.event_kind,
    }


@staff_router.get("/api/staff/gatherings")
async def api_staff_gatherings(request: Request):
    _require_staff(request)
    ctx = _ctx(request)
    events = await ctx.plus.list_events(status="active") if ctx.plus else []
    return {"gatherings": [_event_json(e) for e in events]}


@staff_router.post("/api/staff/gatherings")
async def api_staff_create_gathering(
    request: Request,
    kind: str = Form("general"),
    reason: str = Form(""),
    event_time: str = Form(""),
    need_static: bool = Form(False),
    title: str = Form(""),
):
    user = _require_staff(request)
    ctx = _ctx(request)
    guild = ctx.guild
    if guild is None:
        return _error_json(500, "Бот не на сервере")
    channel = guild.get_channel(PLUS_DEF_CHANNEL_ID)
    if channel is None:
        return _error_json(500, "Не задан PLUS_DEF_CHANNEL_ID")
    if kind not in PLUS_KIND_LABELS:
        return _error_json(400, "Неизвестный тип сбора")
    try:
        event_time_dt = datetime.strptime(event_time, "%Y-%m-%dT%H:%M")
    except ValueError:
        return _error_json(400, "Неверный формат времени")
    event_time_dt = event_time_dt.replace(tzinfo=ZoneInfo(MOSCOW_TZ))
    event = await ctx.plus.create_event(
        channel,
        creator_id=user["uid"],
        title=title.strip() or None,
        reason=reason.strip(),
        event_time=event_time_dt,
        need_static=need_static,
        kind=kind,
        ping_role=PLUS_KIND_PINGS.get(kind) or None,
    )
    if event is None:
        return _error_json(500, "Не удалось создать сбор")
    return JSONResponse({"ok": True, "id": event.id})
