from __future__ import annotations

from dataclasses import dataclass

from saint_jerome.app.services.guild_liturgy_service import GuildLiturgyRepository
from saint_jerome.domain.liturgy import GuildLiturgySubscription
from saint_jerome.infra.database import PostgresPoolFactory


@dataclass(slots=True)
class PostgresGuildLiturgyRepository(GuildLiturgyRepository):
    pool_factory: PostgresPoolFactory

    async def initialize(self) -> None:
        pool = await self.pool_factory.get_pool()
        await pool.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_liturgy_settings (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                post_hour INTEGER NOT NULL,
                post_minute INTEGER NOT NULL,
                timezone TEXT NOT NULL,
                include_prayers BOOLEAN NOT NULL DEFAULT TRUE,
                include_antiphons BOOLEAN NOT NULL DEFAULT TRUE,
                include_extras BOOLEAN NOT NULL DEFAULT TRUE,
                last_sent_date TEXT NULL
            )
            """
        )

    async def get_subscription(self, guild_id: int) -> GuildLiturgySubscription | None:
        pool = await self.pool_factory.get_pool()
        row = await pool.fetchrow(
            """
            SELECT guild_id, channel_id, enabled, post_hour, post_minute, timezone,
                   include_prayers, include_antiphons, include_extras, last_sent_date
            FROM guild_liturgy_settings
            WHERE guild_id = $1
            """,
            guild_id,
        )
        return self._row_to_subscription(row) if row else None

    async def upsert_subscription(self, subscription: GuildLiturgySubscription) -> None:
        pool = await self.pool_factory.get_pool()
        await pool.execute(
            """
            INSERT INTO guild_liturgy_settings (
                guild_id, channel_id, enabled, post_hour, post_minute, timezone,
                include_prayers, include_antiphons, include_extras, last_sent_date
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id = excluded.channel_id,
                enabled = excluded.enabled,
                post_hour = excluded.post_hour,
                post_minute = excluded.post_minute,
                timezone = excluded.timezone,
                include_prayers = excluded.include_prayers,
                include_antiphons = excluded.include_antiphons,
                include_extras = excluded.include_extras,
                last_sent_date = excluded.last_sent_date
            """,
            subscription.guild_id,
            subscription.channel_id,
            subscription.enabled,
            subscription.post_hour,
            subscription.post_minute,
            subscription.timezone,
            subscription.include_prayers,
            subscription.include_antiphons,
            subscription.include_extras,
            subscription.last_sent_date,
        )

    async def disable_subscription(self, guild_id: int) -> None:
        pool = await self.pool_factory.get_pool()
        await pool.execute(
            """
            UPDATE guild_liturgy_settings
            SET enabled = FALSE
            WHERE guild_id = $1
            """,
            guild_id,
        )

    async def list_enabled_subscriptions(self) -> list[GuildLiturgySubscription]:
        pool = await self.pool_factory.get_pool()
        rows = await pool.fetch(
            """
            SELECT guild_id, channel_id, enabled, post_hour, post_minute, timezone,
                   include_prayers, include_antiphons, include_extras, last_sent_date
            FROM guild_liturgy_settings
            WHERE enabled = TRUE
            """
        )
        return [self._row_to_subscription(row) for row in rows]

    async def mark_sent(self, guild_id: int, sent_date: str) -> None:
        pool = await self.pool_factory.get_pool()
        await pool.execute(
            """
            UPDATE guild_liturgy_settings
            SET last_sent_date = $1
            WHERE guild_id = $2
            """,
            sent_date,
            guild_id,
        )

    @staticmethod
    def _row_to_subscription(row) -> GuildLiturgySubscription:
        return GuildLiturgySubscription(
            guild_id=int(row["guild_id"]),
            channel_id=int(row["channel_id"]),
            enabled=bool(row["enabled"]),
            post_hour=int(row["post_hour"]),
            post_minute=int(row["post_minute"]),
            timezone=str(row["timezone"]),
            include_prayers=bool(row["include_prayers"]),
            include_antiphons=bool(row["include_antiphons"]),
            include_extras=bool(row["include_extras"]),
            last_sent_date=row["last_sent_date"],
        )
