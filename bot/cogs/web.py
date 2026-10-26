"""Запуск сайта внутри процесса бота (FastAPI + uvicorn в том же event loop)."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import uvicorn
from discord.ext import commands

from bot.config import GUILD_ID, Settings
from bot.web.app import create_app
from bot.web.context import WebContext
from bot.web.online import OnlineCache

log = logging.getLogger("akiyama.web")


class WebCog(commands.Cog, name="Web"):
    """Сайт akiyama-5rp.ru: публичные страницы + панель стаффа."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings: Settings = getattr(bot, "settings", None) or Settings()
        self.ctx: WebContext | None = None
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task[None] | None = None
        self.online: OnlineCache | None = None

    async def cog_load(self) -> None:
        settings = self.settings
        if not settings.web_secret:
            log.warning(
                "WEB_SECRET пуста — сессии панели будут невозможны; задайте его в .env"
            )
        self.online = OnlineCache(
            api_url=settings.online_api_url,
            server_id=settings.online_server_id,
            server_name=settings.online_server_name,
        )
        self.online.start()
        self.ctx = WebContext(
            settings=settings,
            bot=self.bot,
            online=self.online,
            secret=settings.web_secret or "insecure-dev-secret",
        )
        static_dir = Path(settings.web_static_dir)
        app = create_app(self.ctx, static_dir=static_dir if static_dir.is_dir() else None)
        config = uvicorn.Config(
            app,
            host=settings.web_host,
            port=settings.web_port,
            log_level="info",
            access_log=True,
        )
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._serve())
        log.info("web: uvicorn на %s:%s (guild=%s)", settings.web_host, settings.web_port, GUILD_ID)

    async def _serve(self) -> None:
        assert self._server is not None
        await self._server.serve()

    async def cog_unload(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except (TimeoutError, asyncio.CancelledError):
                self._task.cancel()
            self._task = None
        if self.online is not None:
            await self.online.stop()
        log.info("web: uvicorn остановлен")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WebCog(bot))
