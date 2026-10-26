"""Онлайн-статистика сервера (gta5masterlist.ru, публичный JSON).

Фетчит JSON с периодом ONLINE_POLL_SECONDS и держит результат в памяти.
API-URL берётся из конфига — templates: {server_id} подставляется ID сервера.
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
        self.online_names: list[str] = []
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
        url = self._api_url.format(server_id=self._server_id)
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        self._apply(data)

    def _apply(self, data: Any) -> None:
        count, names = self._parse(data)
        self.online_count = count
        self.online_names = names
        self.updated = time.time()
        self.error = None

    @staticmethod
    def _parse(data: Any) -> tuple[int | None, list[str]]:
        """Толерантный разбор ответа — принимаем known форматы JSON."""
        if isinstance(data, dict):
            for key in ("online", "online_count", "onlineCount", "players", "player_count"):
                value = data.get(key)
                if isinstance(value, int):
                    return value, []
                if isinstance(value, list):
                    return len(value), [str(item) for item in value]
            names = data.get("online_nicks") or data.get("names")
            if isinstance(names, list):
                return len(names), [str(item) for item in names]
            return None, []
        if isinstance(data, list):
            return len(data), [str(item) for item in data]
        return None, []
