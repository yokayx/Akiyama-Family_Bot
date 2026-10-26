"""Совместный контекст для веб-приложения (ссылки на cogs, конфиг, онлайн-кэш)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bot.config import GUILD_ID, Settings

if TYPE_CHECKING:
    from discord.ext.commands import Bot

    from bot.cogs.applications import ApplicationsCog
    from bot.cogs.plus import PlusCog
    from bot.roster.manager import RosterManager
    from bot.web.online import OnlineCache


def _has_methods(cog: Any, *names: str) -> bool:
    return all(callable(getattr(cog, name, None)) for name in names)


@dataclass
class WebContext:
    settings: Settings
    bot: Bot
    online: OnlineCache
    secret: str
    extra: dict = field(default_factory=dict)

    @property
    def guild(self):
        return self.bot.get_guild(GUILD_ID)

    @property
    def applications(self) -> ApplicationsCog | None:
        cog = self.bot.get_cog("Applications")
        if cog is None or not _has_methods(cog, "list_tickets", "claim_ticket"):
            return None
        return cog

    @property
    def plus(self) -> PlusCog | None:
        cog = self.bot.get_cog("Plus")
        if cog is None or not _has_methods(cog, "list_events", "create_event"):
            return None
        return cog

    @property
    def roster(self) -> RosterManager | None:
        cog = self.bot.get_cog("Roster")
        manager = getattr(cog, "manager", None)
        if manager is None or not _has_methods(manager, "build_payload"):
            return None
        return manager
