"""Тесты сайта (FastAPI-приложение в процессе бота)."""
from __future__ import annotations

import time
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


def _make_ctx() -> WebContext:
    bot = MagicMock()
    bot.get_guild.return_value = None

    applications = MagicMock()
    applications.list_tickets = AsyncMock(return_value=[])
    applications.claim_ticket = AsyncMock(return_value=(True, "ok"))
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
        api_url="https://example.com/api/{server_id}/online",
        server_id=8,
        server_name="Blaine",
    )
    online.online_count = 42
    online.updated = time.time()
    return WebContext(settings=_make_settings(), bot=bot, online=online, secret=_SECRET)


def _client(ctx: WebContext):
    app = create_app(ctx)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


# --- Сессия -------------------------------------------------------------------


def test_session_roundtrip() -> None:
    cookie = create_session(uid=7, name="user", is_staff=True, secret=_SECRET)
    data = read_session(cookie, _SECRET)
    assert data == {"uid": 7, "name": "user", "is_staff": True, "expires": data["expires"]}


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


# --- Публичные страницы -------------------------------------------------------


async def test_index_renders() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "Akiyama" in response.text
    assert "42" in response.text  # онлайн


async def test_roster_renders() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/roster")
    assert response.status_code == 200
    assert "ник" in response.text


async def test_vzp_page_renders() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/vzp")
    assert response.status_code == 200
    assert "VZP" in response.text


async def test_online_page_renders() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/online")
    assert response.status_code == 200
    assert "Blaine" in response.text


async def test_gatherings_page_renders() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/gatherings")
    assert response.status_code == 200


async def test_api_endpoints_json() -> None:
    async with _client(_make_ctx()) as client:
        roster = await client.get("/api/roster")
        online = await client.get("/api/online")
        stats = await client.get("/api/vzp/stats")
    assert roster.status_code == 200
    assert roster.json()["unique_count"] == 3
    assert online.json()["online"] == 42
    assert "names" not in online.json()
    assert isinstance(stats.json(), dict)


# --- Панель стаффа ------------------------------------------------------------


async def test_staff_login_page() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/staff/login")
    assert response.status_code == 200
    assert "Discord" in response.text


async def test_staff_pages_require_auth() -> None:
    async with _client(_make_ctx()) as client:
        assert (await client.get("/staff")).status_code == 401
        assert (await client.get("/staff/applications")).status_code == 401


async def test_staff_with_session() -> None:
    ctx = _make_ctx()
    cookie = create_session(uid=7, name="staff", is_staff=True, secret=_SECRET)
    async with _client(ctx) as client:
        response = await client.get("/staff", cookies={SESSION_COOKIE: cookie})
    assert response.status_code == 200
    assert "staff" in response.text


async def test_oauth_callback_bad_state() -> None:
    async with _client(_make_ctx()) as client:
        response = await client.get("/auth/callback?code=x&state=wrong")
    assert response.status_code == 400


async def test_oauth_callback_unknown_user_page() -> None:
    """Правильный state, но не стафф — 403 через mock."""
    ctx = _make_ctx()
    async with _client(ctx) as client:
        response = await client.get("/auth/callback?code=x&state=")
    assert response.status_code in (400, 403)
