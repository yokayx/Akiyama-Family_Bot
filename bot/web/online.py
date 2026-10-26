"""Онлайн-статистика сервера (gta5masterlist.ru, публичный JSON).

API /api/servers возвращает лист серверов (gta5rp/majestic/...), каждый со
serverId, name и currentOnline. Мы фильтруем по online_server_id и кэшим
результат с периодом ONLINE_POLL_SECONDS.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

log = logging.getLogger("akiyama.web.online")

ONLINE_POLL_SECONDS = 60


class OnlineCache:
    """Полноценно обновляет данные раз в ONLINE_POLL_SECONDS, внутри одного цикла."""

    def __init__(
        self,
        *,
        api_url: str,
        server_id: int,
        server_name: str,
        poll_seconds: int = ONLINE_POLL_SECONDS,
    ) -> None:
        self._api_url = api_url
        self._server_id = server_id
        self.server_name = server_name
        self._poll_seconds = max(15, poll_seconds)
        self.online_count: int | None = None
        self.updated: float | None = None
        self.error: str | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                await self.fetch()
            except Exception as exc:  # noqa: BLE001 — онлайн — сервис, не критичный
                log.warning("online fetch failed: %s", exc)
            await asyncio.sleep(self._poll_seconds)

    async def fetch(self) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(self._api_url)
            response.raise_for_status()
            data = response.json()
        self._apply(data)

    def _apply(self, data: Any) -> None:
        self.online_count = self._find_online(data)
        self.updated = time.time()
        self.error = None

    def _find_online(self, data: Any) -> int | None:
        """currentOnline сервера с нашим serverId. None, если не нашёл."""
        for server in self._server_list(data):
            if str(server.get("serverId")) == str(self._server_id):
                online = server.get("currentOnline")
                return online if isinstance(online, int) else None
        return None

    @staticmethod
    def _server_list(data: Any) -> list[dict]:
        """/api/servers → лист всех серверов (nested по проектам)."""
        if isinstance(data, list):
            return [s for s in data if isinstance(s, dict)]
        if isinstance(data, dict):
            # Случайный сервер как один объект (специфичный endpoint).
            if "serverId" in data or "currentOnline" in data:
                return [data]
            for key in ("gta5rp", "majestic", "russiaonline", "servers", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    return [s for s in value if isinstance(s, dict)]
        return []
