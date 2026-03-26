from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from saint_jerome.app.services.guild_liturgy_service import GuildLiturgyService
from saint_jerome.domain.liturgy import GuildLiturgySubscription


class FakeGuildLiturgyRepository:
    def __init__(self) -> None:
        self.items: dict[int, GuildLiturgySubscription] = {}

    async def initialize(self) -> None:
        return None

    async def get_subscription(self, guild_id: int) -> GuildLiturgySubscription | None:
        return self.items.get(guild_id)

    async def upsert_subscription(self, subscription: GuildLiturgySubscription) -> None:
        self.items[subscription.guild_id] = subscription

    async def disable_subscription(self, guild_id: int) -> None:
        current = self.items[guild_id]
        self.items[guild_id] = GuildLiturgySubscription(
            guild_id=current.guild_id,
            channel_id=current.channel_id,
            enabled=False,
            post_hour=current.post_hour,
            post_minute=current.post_minute,
            timezone=current.timezone,
            include_prayers=current.include_prayers,
            include_antiphons=current.include_antiphons,
            include_extras=current.include_extras,
            last_sent_date=current.last_sent_date,
        )

    async def list_enabled_subscriptions(self) -> list[GuildLiturgySubscription]:
        return [item for item in self.items.values() if item.enabled]

    async def mark_sent(self, guild_id: int, sent_date: str) -> None:
        current = self.items[guild_id]
        self.items[guild_id] = GuildLiturgySubscription(
            guild_id=current.guild_id,
            channel_id=current.channel_id,
            enabled=current.enabled,
            post_hour=current.post_hour,
            post_minute=current.post_minute,
            timezone=current.timezone,
            include_prayers=current.include_prayers,
            include_antiphons=current.include_antiphons,
            include_extras=current.include_extras,
            last_sent_date=sent_date,
        )


def test_due_subscriptions_respect_timezone_and_last_sent_date() -> None:
    async def scenario() -> None:
        repository = FakeGuildLiturgyRepository()
        service = GuildLiturgyService(
            repository=repository,
            default_timezone="America/Sao_Paulo",
        )

        await service.configure(
            guild_id=1,
            channel_id=10,
            hour=8,
            minute=30,
            timezone="America/Sao_Paulo",
        )

        due = await service.get_due_subscriptions(
            now_utc=datetime(2026, 3, 25, 11, 30, tzinfo=UTC)
        )
        assert due == [(repository.items[1], "2026-03-25")]

        await service.mark_sent(1, "2026-03-25")
        due_again = await service.get_due_subscriptions(
            now_utc=datetime(2026, 3, 25, 11, 30, tzinfo=UTC)
        )
        assert due_again == []

    asyncio.run(scenario())
