"""Тесты сайта (FastAPI: JSON API + хостинг React SPA)."""
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bot.config import Settings
from bot.db import init_db
from bot.roster.builder import RosterPayload
from bot.web.app import create_app
from bot.web.context import WebContext
from bot.web.oauth import build_authorize_url
from bot.web.online import OnlineCache
from bot.web.session import SESSION_COOKIE, create_session, read_session

_SECRET = "test-secret"


@pytest.fixture(autouse=True)
async def _db():
    """Сайту нужна БД: инициализируем в оперативную sqlite."""
    await init_db("sqlite+aiosqlite:///:memory:")


def _make_settings() -> Settings:
    return Settings(
        discord_token="test",
        web_secret=_SECRET,
        oauth_client_id="cid",
        oauth_client_secret="csec",
        oauth_redirect_uri="https://akiyama-5rp.ru/auth/callback",
    )


class _StubTicket:
    """Минимальная Ticket для тестов API."""

    id = 5
    channel_id = 12345
    applicant_id = 999
    kind = "main"
    handler_id = None
    status = "open"
    answers_json = '[{"question": "Сколько лет?", "answer": "20"}]'
    applicant_replied = False
    rejection_reason = None
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    claimed_at = None
    closed_at = None


def _make_ctx() -> WebContext:
    bot = MagicMock()
    bot.get_guild.return_value = None

    applications = MagicMock()
    applications.list_tickets = AsyncMock(return_value=[])
    applications.claim_ticket = AsyncMock(return_value=(True, "ok"))
    applications.get_ticket = AsyncMock(return_value=_StubTicket())
    plus = MagicMock()
    plus.list_events = AsyncMock(return_value=[])
    plus.create_event = AsyncMock(return_value=None)
    roster = MagicMock()
    roster.build_payload = AsyncMock(
        return_value=RosterPayload(
            messages=("## Sec\n- ник",), unique_count=3, member_ids=frozenset({1})
        )
    )
    bot.get_cog.side_effect = lambda name: {
        "Applications": applications,
        "Plus": plus,
        "Roster": MagicMock(manager=roster),
    }.get(name)

    online = OnlineCache(
        api_url="https://example.com/api/servers",
        server_id=27,
        server_name="Blaine",
    )
    online.online_count = 5499
    online.updated = time.time()
    return WebContext(settings=_make_settings(), bot=bot, online=online, secret=_SECRET)


def _client(ctx: WebContext, static_dir: Path | None = None):
    app = create_app(ctx, static_dir=static_dir)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


# --- Сессия -------------------------------------------------------------------


def test_session_roundtrip() -> None:
    cookie = create_session(uid=7, name="user", is_staff=True, secret=_SECRET)
    data = read_session(cookie, _SECRET)
    assert data is not None
    assert data["uid"] == 7
    assert data["is_staff"] is True


def test_session_tamper_rejected() -> None:
    cookie = create_session(uid=7, name="u", is_staff=True, secret=_SECRET)
    body, sig = cookie.rsplit(".", 1)
    assert read_session(f"{body}.0000", _SECRET) is None
    assert read_session(cookie, "other-secret") is None
    assert read_session(None, _SECRET) is None
    assert read_session("no-dot", _SECRET) is None


def test_session_expired_rejected() -> None:
    cookie = create_session(uid=7, name="u", is_staff=True, secret=_SECRET, ttl=-1)
    assert read_session(cookie, _SECRET) is None


# --- OAuth --------------------------------------------------------------------


def test_oauth_url_contains_params() -> None:
    url = build_authorize_url(
        client_id="cid", redirect_uri="https://akiyama-5rp.ru/auth/callback", state="st"
    )
    assert "discord.com/oauth2/authorize" in url
    assert "client_id=cid" in url
    assert "state=st" in url
    assert "scope=identify+guilds" in url or "scope=identify%20guilds" in url


async def test_oauth_callback_bad_state() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/auth/callback?code=x&state=wrong")
    assert response.status_code == 400
    assert response.json()["ok"] is False


# --- Онлайн-кэш ---------------------------------------------------------------


def _cache() -> OnlineCache:
    return OnlineCache(
        api_url="https://example.com/api/servers", server_id=27, server_name="Blaine"
    )


def test_online_finds_server_in_list() -> None:
    """/api/servers → вложенный лист по проектам, фильтр по serverId."""
    data = {
        "gta5rp": [
            {"serverId": 26, "name": "Mirror", "currentOnline": 3377},
            {"serverId": 27, "name": "Blaine", "currentOnline": 5499},
        ]
    }
    assert _cache()._find_online(data) == 5499


def test_online_single_server_object() -> None:
    data = {"serverId": 27, "name": "Blaine", "currentOnline": 42}
    assert _cache()._find_online(data) == 42


def test_online_bare_list() -> None:
    data = [{"serverId": 27, "currentOnline": 7}]
    assert _cache()._find_online(data) == 7


def test_online_unknown_server() -> None:
    assert _cache()._find_online({"gta5rp": [{"serverId": 99}]}) is None
    assert _cache()._find_online({"weird": True}) is None


# --- Публичный JSON API -------------------------------------------------------


async def test_public_api_endpoints() -> None:
    async with _client(_make_ctx()) as client:
        roster = await client.get("/api/roster")
        online = await client.get("/api/online")
        stats = await client.get("/api/vzp/stats")
        wars = await client.get("/api/vzp/wars")
        top = await client.get("/api/vzp/top")
        gatherings = await client.get("/api/gatherings")
    assert roster.json()["unique_count"] == 3
    assert online.json()["online"] == 5499
    assert isinstance(stats.json(), dict)
    assert isinstance(wars.json()["wars"], list)
    assert isinstance(top.json()["top"], list)
    assert gatherings.json()["gatherings"] == []


# --- Панель стаффа (JSON API) -------------------------------------------------


async def test_api_me_requires_session() -> None:
    async with _client(_make_ctx()) as client:
        assert (await client.get("/api/me")).status_code == 401


async def test_api_me_with_session() -> None:
    cookie = create_session(uid=7, name="staff", is_staff=True, secret=_SECRET)
    async with _client(_make_ctx()) as client:
        response = await client.get("/api/me", cookies={SESSION_COOKIE: cookie})
    assert response.status_code == 200
    assert response.json() == {"uid": 7, "name": "staff", "is_staff": True}


async def test_staff_login_url() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/api/staff/login-url")
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://discord.com/oauth2/authorize")


async def test_staff_tickets_require_session() -> None:
    async with _client(_make_ctx()) as client:
        assert (await client.get("/api/staff/tickets")).status_code == 401


async def test_staff_tickets_list() -> None:
    cookie = create_session(uid=7, name="staff", is_staff=True, secret=_SECRET)
    async with _client(_make_ctx()) as client:
        response = await client.get("/api/staff/tickets", cookies={SESSION_COOKIE: cookie})
    assert response.status_code == 200
    assert response.json()["tickets"] == []


async def test_staff_ticket_detail() -> None:
    cookie = create_session(uid=7, name="staff", is_staff=True, secret=_SECRET)
    async with _client(_make_ctx()) as client:
        response = await client.get(
            "/api/staff/tickets/5", cookies={SESSION_COOKIE: cookie}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 5
    assert body["status"] == "open"
    assert body["answers"][0]["answer"] == "20"


async def test_staff_ticket_claim() -> None:
    cookie = create_session(uid=7, name="staff", is_staff=True, secret=_SECRET)
    async with _client(_make_ctx()) as client:
        response = await client.post(
            "/api/staff/tickets/5/claim", cookies={SESSION_COOKIE: cookie}
        )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "ok"}


async def test_staff_gatherings_list() -> None:
    cookie = create_session(uid=7, name="staff", is_staff=True, secret=_SECRET)
    async with _client(_make_ctx()) as client:
        response = await client.get(
            "/api/staff/gatherings", cookies={SESSION_COOKIE: cookie}
        )
    assert response.status_code == 200
    assert response.json()["gatherings"] == []


async def test_staff_create_gathering_no_channel() -> None:
    """Без guild (bot.get_guild → None) — 500 с ошибкой, не падение."""
    cookie = create_session(uid=7, name="staff", is_staff=True, secret=_SECRET)
    async with _client(_make_ctx()) as client:
        response = await client.post(
            "/api/staff/gatherings",
            cookies={SESSION_COOKIE: cookie},
            data={"kind": "general", "reason": "x", "event_time": "2026-12-01T20:00"},
        )
    assert response.status_code == 500
    assert response.json()["ok"] is False


# --- Health -------------------------------------------------------------------

async def test_health_endpoint() -> None:
    """Эндпоинт для мониторинга и проверки HTTPS после настройки прокси."""
    async with _client(_make_ctx()) as client:
        response = await client.get("/api/health")
        head = await client.head("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert head.status_code == 200  # curl -I (HEAD) должен работать


# --- SPA хостинг --------------------------------------------------------------


async def test_spa_fallback_serves_index(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html><body>SPA</body></html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    async with _client(_make_ctx(), static_dir=tmp_path) as client:
        root = await client.get("/")
        client_route = await client.get("/staff/applications")
        asset = await client.get("/assets/app.js")
    assert root.status_code == 200
    assert "SPA" in root.text
    assert "SPA" in client_route.text  # client-side route → index.html
    assert asset.status_code == 200
    assert "console.log" in asset.text
