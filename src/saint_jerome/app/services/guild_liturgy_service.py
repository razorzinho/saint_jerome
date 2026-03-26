from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from saint_jerome.domain.liturgy import GuildLiturgySubscription

logger = logging.getLogger("saint_jerome.guild_liturgy")


class GuildLiturgyRepository:
    async def initialize(self) -> None:
        raise NotImplementedError

    async def get_subscription(self, guild_id: int) -> GuildLiturgySubscription | None:
        raise NotImplementedError

    async def upsert_subscription(self, subscription: GuildLiturgySubscription) -> None:
        raise NotImplementedError

    async def disable_subscription(self, guild_id: int) -> None:
        raise NotImplementedError

    async def list_enabled_subscriptions(self) -> list[GuildLiturgySubscription]:
        raise NotImplementedError

    async def mark_sent(self, guild_id: int, sent_date: str) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class GuildLiturgyService:
    repository: GuildLiturgyRepository
    default_timezone: str

    async def initialize(self) -> None:
        await self.repository.initialize()

    async def configure(
        self,
        *,
        guild_id: int,
        channel_id: int,
        hour: int,
        minute: int,
        timezone: str | None = None,
        include_prayers: bool = True,
        include_antiphons: bool = True,
        include_extras: bool = True,
    ) -> GuildLiturgySubscription:
        if not 0 <= hour <= 23:
            raise ValueError("A hora deve estar entre 0 e 23.")
        if not 0 <= minute <= 59:
            raise ValueError("O minuto deve estar entre 0 e 59.")

        resolved_timezone = timezone or self.default_timezone
        self._validate_timezone(resolved_timezone)

        current = await self.repository.get_subscription(guild_id)
        subscription = GuildLiturgySubscription(
            guild_id=guild_id,
            channel_id=channel_id,
            enabled=True,
            post_hour=hour,
            post_minute=minute,
            timezone=resolved_timezone,
            include_prayers=include_prayers,
            include_antiphons=include_antiphons,
            include_extras=include_extras,
            last_sent_date=current.last_sent_date if current else None,
        )
        await self.repository.upsert_subscription(subscription)
        return subscription

    async def get_subscription(self, guild_id: int) -> GuildLiturgySubscription | None:
        return await self.repository.get_subscription(guild_id)

    async def disable(self, guild_id: int) -> None:
        await self.repository.disable_subscription(guild_id)

    async def get_due_subscriptions(
        self,
        *,
        now_utc: datetime | None = None,
    ) -> list[tuple[GuildLiturgySubscription, str]]:
        now = now_utc or datetime.now(UTC)
        due: list[tuple[GuildLiturgySubscription, str]] = []

        for subscription in await self.repository.list_enabled_subscriptions():
            try:
                timezone = self._build_zoneinfo(subscription.timezone)
            except ValueError:
                logger.warning(
                    "Skipping guild %s because timezone %s is invalid or unavailable.",
                    subscription.guild_id,
                    subscription.timezone,
                )
                continue

            local_now = now.astimezone(timezone)
            local_date = local_now.date().isoformat()

            if subscription.last_sent_date == local_date:
                continue
            if local_now.hour != subscription.post_hour:
                continue
            if local_now.minute != subscription.post_minute:
                continue

            due.append((subscription, local_date))

        return due

    async def mark_sent(self, guild_id: int, sent_date: str) -> None:
        await self.repository.mark_sent(guild_id, sent_date)

    @staticmethod
    def _validate_timezone(timezone: str) -> None:
        GuildLiturgyService._build_zoneinfo(timezone)

    @staticmethod
    def _build_zoneinfo(timezone: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                "Timezone inválida ou base de timezones indisponível. "
                "Exemplo válido: America/Sao_Paulo."
            ) from exc
