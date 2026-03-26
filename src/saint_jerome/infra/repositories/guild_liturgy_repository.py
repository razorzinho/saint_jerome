from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from saint_jerome.app.services.guild_liturgy_service import GuildLiturgyRepository
from saint_jerome.domain.liturgy import GuildLiturgySubscription


@dataclass(slots=True)
class SQLiteGuildLiturgyRepository(GuildLiturgyRepository):
    db_path: Path

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_liturgy_settings (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    post_hour INTEGER NOT NULL,
                    post_minute INTEGER NOT NULL,
                    timezone TEXT NOT NULL,
                    include_prayers INTEGER NOT NULL DEFAULT 1,
                    include_antiphons INTEGER NOT NULL DEFAULT 1,
                    include_extras INTEGER NOT NULL DEFAULT 1,
                    last_sent_date TEXT NULL
                )
                """
            )
            await db.commit()

    async def get_subscription(self, guild_id: int) -> GuildLiturgySubscription | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT guild_id, channel_id, enabled, post_hour, post_minute, timezone,
                       include_prayers, include_antiphons, include_extras, last_sent_date
                FROM guild_liturgy_settings
                WHERE guild_id = ?
                """,
                (guild_id,),
            )
            row = await cursor.fetchone()
            return self._row_to_subscription(row) if row else None

    async def upsert_subscription(self, subscription: GuildLiturgySubscription) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO guild_liturgy_settings (
                    guild_id, channel_id, enabled, post_hour, post_minute, timezone,
                    include_prayers, include_antiphons, include_extras, last_sent_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                (
                    subscription.guild_id,
                    subscription.channel_id,
                    int(subscription.enabled),
                    subscription.post_hour,
                    subscription.post_minute,
                    subscription.timezone,
                    int(subscription.include_prayers),
                    int(subscription.include_antiphons),
                    int(subscription.include_extras),
                    subscription.last_sent_date,
                ),
            )
            await db.commit()

    async def disable_subscription(self, guild_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE guild_liturgy_settings
                SET enabled = 0
                WHERE guild_id = ?
                """,
                (guild_id,),
            )
            await db.commit()

    async def list_enabled_subscriptions(self) -> list[GuildLiturgySubscription]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT guild_id, channel_id, enabled, post_hour, post_minute, timezone,
                       include_prayers, include_antiphons, include_extras, last_sent_date
                FROM guild_liturgy_settings
                WHERE enabled = 1
                """
            )
            rows = await cursor.fetchall()
            return [self._row_to_subscription(row) for row in rows]

    async def mark_sent(self, guild_id: int, sent_date: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE guild_liturgy_settings
                SET last_sent_date = ?
                WHERE guild_id = ?
                """,
                (sent_date, guild_id),
            )
            await db.commit()

    @staticmethod
    def _row_to_subscription(row: aiosqlite.Row) -> GuildLiturgySubscription:
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
