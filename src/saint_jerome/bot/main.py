from __future__ import annotations

import logging
import sqlite3
from typing import Awaitable, Callable

import discord
from discord.ext import commands

from saint_jerome.app.services.bible_service import BibleService
from saint_jerome.app.services.guild_liturgy_service import GuildLiturgyService
from saint_jerome.app.services.liturgy_service import LiturgyService
from saint_jerome.bot.client import BotContainer, build_container
from saint_jerome.config.settings import Settings
from saint_jerome.infra.clients.liturgy_api import RailwayLiturgyClient
from saint_jerome.infra.database import PostgresPoolFactory
from saint_jerome.infra.loaders.json_loader import load_json_file
from saint_jerome.infra.repositories.guild_liturgy_repository import (
    SQLiteGuildLiturgyRepository,
)
from saint_jerome.infra.repositories.memory_repository import MemoryBibleRepository
from saint_jerome.infra.repositories.postgres_bible_repository import (
    PostgresBibleRepository,
)
from saint_jerome.infra.repositories.postgres_guild_liturgy_repository import (
    PostgresGuildLiturgyRepository,
)
from saint_jerome.infra.repositories.sqlite_repository import SQLiteBibleRepository

logger = logging.getLogger("saint_jerome")


class SaintJeromeBot(commands.Bot):
    container: BotContainer

    async def setup_hook(self) -> None:
        await self.container.guild_liturgy_service.initialize()

        await self.load_extension("saint_jerome.bot.cogs.bible_cog")
        await self.load_extension("saint_jerome.bot.cogs.liturgy_cog")
        logger.info("Loaded extensions: bible_cog, liturgy_cog")

        if self.container.settings.sync_commands_on_startup:
            await self.tree.sync()
            logger.info("Slash commands synced.")

    async def close(self) -> None:
        await self.container.close()
        await super().close()

    async def on_ready(self) -> None:
        user_id = self.user.id if self.user else "unknown"
        logger.info("Bot is ready! Logged in as %s (ID: %s)", self.user, user_id)


def create_bot(settings: Settings) -> SaintJeromeBot:
    repository, guild_repository, default_translation, shutdown_callbacks = build_data_access(
        settings
    )
    bible_service = BibleService(
        repository=repository,
        default_translation=default_translation,
    )

    liturgy_service = LiturgyService(
        client=RailwayLiturgyClient(
            base_url=settings.liturgy_api_base_url,
            timeout_seconds=settings.liturgy_request_timeout_seconds,
        )
    )
    guild_liturgy_service = GuildLiturgyService(
        repository=guild_repository,
        default_timezone=settings.default_timezone,
    )
    container = build_container(
        bible_service=bible_service,
        liturgy_service=liturgy_service,
        guild_liturgy_service=guild_liturgy_service,
        settings=settings,
        shutdown_callbacks=shutdown_callbacks,
    )

    intents = discord.Intents.default()
    intents.message_content = True

    bot = SaintJeromeBot(
        command_prefix="!",
        intents=intents,
        help_command=None,
    )
    bot.container = container
    return bot


def build_data_access(
    settings: Settings,
) -> tuple[
    MemoryBibleRepository | SQLiteBibleRepository | PostgresBibleRepository,
    SQLiteGuildLiturgyRepository | PostgresGuildLiturgyRepository,
    str,
    tuple[Callable[[], Awaitable[None]], ...],
]:
    default_translation = _resolve_default_translation(settings.default_translation)

    if settings.uses_postgres:
        pool_factory = PostgresPoolFactory(
            dsn=settings.database_url,
            min_size=settings.database_pool_min_size,
            max_size=settings.database_pool_max_size,
        )
        logger.info("Using Postgres repositories")
        return (
            PostgresBibleRepository(pool_factory),
            PostgresGuildLiturgyRepository(pool_factory),
            default_translation,
            (pool_factory.close,),
        )

    if _has_imported_bible(settings.database_file):
        repository = SQLiteBibleRepository(settings.database_file)
        logger.info("Using SQLiteBibleRepository with database %s", settings.database_file)
        return (
            repository,
            SQLiteGuildLiturgyRepository(settings.database_file),
            default_translation,
            (),
        )

    payload = load_json_file(settings.sample_data_file)
    logger.info("Using MemoryBibleRepository with sample JSON data")
    return (
        MemoryBibleRepository(payload),
        SQLiteGuildLiturgyRepository(settings.database_file),
        "sample_pt",
        (),
    )


def _resolve_default_translation(default_translation: str) -> str:
    if default_translation == "sample_pt":
        return "matos_soares_1956"
    return default_translation


def _has_imported_bible(db_path) -> bool:
    if not db_path.exists():
        return False

    try:
        connection = sqlite3.connect(db_path)
        try:
            row = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'translations'
                """
            ).fetchone()
            if row is None:
                return False

            translation_row = connection.execute(
                "SELECT 1 FROM translations LIMIT 1"
            ).fetchone()
            return translation_row is not None
        finally:
            connection.close()
    except sqlite3.Error:
        return False


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()

    if not settings.discord_token:
        logger.error("DISCORD_TOKEN environment variable not set. Cannot start bot.")
        return

    bot = create_bot(settings)
    bot.run(settings.discord_token)


if __name__ == "__main__":
    run()
