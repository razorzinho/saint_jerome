from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from saint_jerome.app.services.bible_service import BibleService
from saint_jerome.app.services.guild_liturgy_service import GuildLiturgyService
from saint_jerome.app.services.liturgy_service import LiturgyService
from saint_jerome.config.settings import Settings
from saint_jerome.domain.parser import ReferenceParser


@dataclass(slots=True)
class BotContainer:
    parser: ReferenceParser
    bible_service: BibleService
    liturgy_service: LiturgyService
    guild_liturgy_service: GuildLiturgyService
    settings: Settings
    shutdown_callbacks: tuple[Callable[[], Awaitable[None]], ...] = ()

    async def close(self) -> None:
        for callback in self.shutdown_callbacks:
            await callback()


def build_container(
    *,
    bible_service: BibleService,
    liturgy_service: LiturgyService,
    guild_liturgy_service: GuildLiturgyService,
    settings: Settings,
    shutdown_callbacks: tuple[Callable[[], Awaitable[None]], ...] = (),
) -> BotContainer:
    return BotContainer(
        parser=ReferenceParser(),
        bible_service=bible_service,
        liturgy_service=liturgy_service,
        guild_liturgy_service=guild_liturgy_service,
        settings=settings,
        shutdown_callbacks=shutdown_callbacks,
    )
