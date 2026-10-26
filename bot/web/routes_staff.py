"""Панель стаффа: вход через Discord OAuth, заявки и сборы."""
from __future__ import annotations

import json
import secrets as py_secrets
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from bot.config import (
    FAMILY_NAME,
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


def _templates(request: Request):
    return request.app.state.templates


def _current_user(request: Request) -> dict | None:
    ctx = _ctx(request)
    return read_session(request.cookies.get(SESSION_COOKIE), ctx.secret)


def _require_staff(request: Request) -> dict:
    user = _current_user(request)
    if user is None or not user.get("is_staff"):
        raise HTTPException(status_code=401, detail="Требуется вход как стафф")
    return user


def _error(request: Request, title: str, message: str, status_code: int):
    ctx = _ctx(request)
    return _templates(request).TemplateResponse(
        request,
        "error.html",
        {"title": title, "message": message, "site_url": ctx.settings.site_url},
        status_code=status_code,
    )


@staff_router.get("/staff/login", response_class=HTMLResponse)
async def login(request: Request):
    ctx = _ctx(request)
    settings = ctx.settings
    if not settings.oauth_client_id or not settings.oauth_client_secret:
        return _templates(request).TemplateResponse(
            request,
            "error.html",
            {
                "title": "OAuth не настроен",
                "message": "oauth_client_id/oauth_client_secret пусты — заполните .env",
                "site_url": settings.site_url,
            },
            status_code=500,
        )
    if _current_user(request):
        return RedirectResponse("/staff", status_code=302)
    state = py_secrets.token_urlsafe(24)
    request.app.state.oauth_state = state
    url = build_authorize_url(
        client_id=settings.oauth_client_id,
        redirect_uri=settings.oauth_redirect_uri,
        state=state,
    )
    return _templates(request).TemplateResponse(
        request,
        "login.html",
        {"title": "Вход стаффа", "authorize_url": url, "family": FAMILY_NAME},
    )


@staff_router.get("/auth/callback")
async def auth_callback(request: Request, code: str = "", state: str = ""):
    ctx = _ctx(request)
    settings = ctx.settings
    if state != getattr(request.app.state, "oauth_state", None):
        return _error(request, "Неверный state", "Запрос неизвестен — вернитесь к входу.", 400)
    if not code:
        return _error(request, "Нет кода", "OAuth вернул пустой code.", 400)
    token = await exchange_code(
        client_id=settings.oauth_client_id,
        client_secret=settings.oauth_client_secret,
        code=code,
        redirect_uri=settings.oauth_redirect_uri,
    )
    user = await fetch_oauth_user(token["access_token"])
    member = await fetch_guild_member(token["access_token"], GUILD_ID)
    if member is None:
        return _error(request, "Не на сервере", "Аккаунт не найден на сервере family.", 403)
    role_ids = {role["id"] for role in member.get("roles", [])}
    is_staff = bool(role_ids & _STAFF_ROLE_IDS)
    if not is_staff:
        return _error(request, "Не staff", "Нет staff-роли на сервере.", 403)
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


@staff_router.post("/auth/logout")
async def logout():
    response = RedirectResponse("/staff/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@staff_router.get("/staff", response_class=HTMLResponse)
async def staff_dashboard(request: Request) -> HTMLResponse:
    user = _require_staff(request)
    ctx = _ctx(request)
    applications = (
        await ctx.applications.list_tickets(statuses=("open", "claimed"))
        if ctx.applications
        else []
    )
    events = await ctx.plus.list_events(status="active") if ctx.plus else []
    return _templates(request).TemplateResponse(
        request,
        "staff_dashboard.html",
        {
            "title": "Панель · Akiyama",
            "user": user,
            "open_tickets": len(applications),
            "active_events": len(events),
            "online_count": ctx.online.online_count,
            "site_url": ctx.settings.site_url,
        },
    )


@staff_router.get("/staff/applications", response_class=HTMLResponse)
async def staff_applications(
    request: Request, status: str = "open", kind: str = ""
) -> HTMLResponse:
    user = _require_staff(request)
    ctx = _ctx(request)
    if applications_cog := ctx.applications:
        if status == "all":
            tickets = await applications_cog.list_tickets(kind=kind or None)
        else:
            tickets = await applications_cog.list_tickets(
                statuses=(status,), kind=kind or None
            )
    else:
        tickets = []
    return _templates(request).TemplateResponse(
        request,
        "staff_applications.html",
        {
            "title": "Заявки · Панель",
            "user": user,
            "tickets": tickets,
            "status": status,
            "kind": kind,
        },
    )


@staff_router.get("/staff/applications/{ticket_id}", response_class=HTMLResponse)
async def staff_ticket(request: Request, ticket_id: int) -> HTMLResponse:
    user = _require_staff(request)
    ctx = _ctx(request)
    ticket = await ctx.applications.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    try:
        answers = json.loads(ticket.answers_json)
    except json.JSONDecodeError:
        answers = []
    guild = ctx.guild
    applicant_name = guild.get_member(ticket.applicant_id)
    if applicant_name is not None:
        applicant_label = applicant_name.display_name
    else:
        applicant_label = f"user:{ticket.applicant_id}"
    handler = guild.get_member(ticket.handler_id) if ticket.handler_id else None
    return _templates(request).TemplateResponse(
        request,
        "staff_ticket.html",
        {
            "title": f"Заявка #{ticket.id} · Панель",
            "user": user,
            "ticket": ticket,
            "answers": answers,
            "applicant_label": applicant_label,
            "handler_label": handler.display_name if handler else "—",
            "kind_label": "Main" if ticket.kind == "main" else "VZP",
        },
    )


@staff_router.post("/staff/applications/{ticket_id}/claim")
async def staff_claim(request: Request, ticket_id: int):
    user = _require_staff(request)
    ctx = _ctx(request)
    ok, message = await ctx.applications.claim_ticket(ticket_id, user["uid"], f"@{user['name']}")
    if ok:
        return RedirectResponse("/staff/applications?status=open", status_code=302)
    return _flash(request, message, "/staff/applications")


@staff_router.post("/staff/applications/{ticket_id}/release")
async def staff_release(request: Request, ticket_id: int):
    _require_staff(request)
    ctx = _ctx(request)
    ok, _ = await ctx.applications.release_ticket(ticket_id)
    return RedirectResponse("/staff/applications?status=open", status_code=302) if ok else _flash(
        request, "Тикет не найден.", "/staff/applications"
    )


@staff_router.post("/staff/applications/{ticket_id}/accept")
async def staff_accept(request: Request, ticket_id: int):
    _require_staff(request)
    ctx = _ctx(request)
    guild = ctx.guild
    if guild is None:
        raise HTTPException(status_code=500, detail="Бот не на сервере")
    ok, _ = await ctx.applications.accept_ticket(ticket_id, guild)
    return RedirectResponse("/staff/applications?status=open", status_code=302) if ok else _flash(
        request, "Не удалось принять.", "/staff/applications"
    )


@staff_router.post("/staff/applications/{ticket_id}/reject")
async def staff_reject(
    request: Request, ticket_id: int, reason: str = Form("")
):
    _require_staff(request)
    ctx = _ctx(request)
    guild = ctx.guild
    if guild is None:
        raise HTTPException(status_code=500, detail="Бот не на сервере")
    reason_text = reason.strip() or "(без причины)"
    ok, _ = await ctx.applications.reject_ticket(ticket_id, reason_text, guild)
    return RedirectResponse("/staff/applications?status=open", status_code=302) if ok else _flash(
        request, "Не удалось отклонить.", "/staff/applications"
    )


def _flash(request: Request, message: str, target: str) -> RedirectResponse:
    """Показать ошибку-flash — передаём через query (message подписывать не нужно)."""
    return RedirectResponse(
        f"{target}?flash={urllib.parse.quote(message)}", status_code=302
    )


@staff_router.get("/staff/gatherings", response_class=HTMLResponse)
async def staff_gatherings(request: Request) -> HTMLResponse:
    user = _require_staff(request)
    ctx = _ctx(request)
    events = await ctx.plus.list_events(status="active") if ctx.plus else []
    return _templates(request).TemplateResponse(
        request,
        "staff_gatherings.html",
        {"title": "Сборы · Панель", "user": user, "events": events, "moscow": MOSCOW_TZ},
    )


@staff_router.post("/staff/gatherings/create")
async def staff_create_gathering(
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
        raise HTTPException(status_code=500, detail="Бот не на сервере")
    channel = guild.get_channel(PLUS_DEF_CHANNEL_ID)
    if channel is None:
        raise HTTPException(status_code=500, detail="Не задан PLUS_DEF_CHANNEL_ID")
    if kind not in PLUS_KIND_LABELS:
        raise HTTPException(status_code=400, detail="Неизвестный тип сбора")
    try:
        event_time_dt = datetime.strptime(event_time, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Неверный формат времени"
        ) from None
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
        return _flash(request, "Не удалось создать сбор.", "/staff/gatherings")
    return RedirectResponse("/staff/gatherings", status_code=302)
