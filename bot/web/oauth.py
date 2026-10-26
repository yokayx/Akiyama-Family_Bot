"""Discord OAuth для входа стаффа на сайт (identify + guilds scopes)."""
from __future__ import annotations

import urllib.parse

import httpx

OAUTH_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
OAUTH_SCOPES = "identify guilds"
# Нужен ли OAuth-токен для приглашения и проверки ролей на сервере.
OAUTH_GUILD_MEMBER_URL = "/users/@me/guilds/{guild_id}/member"


def build_authorize_url(
    *, client_id: str, redirect_uri: str, state: str, scopes: str = OAUTH_SCOPES
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
    }
    return f"{OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code(
    *, client_id: str, client_secret: str, code: str, redirect_uri: str
) -> dict:
    """code → access_token + refresh_token."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            OAUTH_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()


async def fetch_oauth_user(access_token: str) -> dict:
    """/users/@me — Ник и id пользователя."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


async def fetch_guild_member(access_token: str, guild_id: int) -> dict | None:
    """/users/@me/guilds/{id}/member — роль пользователя на нашем сервере.

    None, если пользователь не на сервере (403/404).
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"https://discord.com/api/users/@me/guilds/{guild_id}/member",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code in (401, 403, 404):
            return None
        response.raise_for_status()
        return response.json()
