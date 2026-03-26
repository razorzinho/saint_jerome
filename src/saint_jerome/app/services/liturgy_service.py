from __future__ import annotations

from dataclasses import dataclass

from saint_jerome.domain.liturgy import DailyLiturgy


class LiturgyClient:
    async def fetch_today(self) -> dict:
        raise NotImplementedError

    async def fetch_by_date(
        self,
        *,
        day: int,
        month: int | None = None,
        year: int | None = None,
    ) -> dict:
        raise NotImplementedError

    async def fetch_period(self, days: int) -> list[dict]:
        raise NotImplementedError


@dataclass(slots=True)
class LiturgyService:
    client: LiturgyClient

    async def get_today(self) -> DailyLiturgy:
        payload = await self.client.fetch_today()
        return DailyLiturgy.from_api_payload(payload)

    async def get_by_date(
        self,
        *,
        day: int,
        month: int | None = None,
        year: int | None = None,
    ) -> DailyLiturgy:
        payload = await self.client.fetch_by_date(day=day, month=month, year=year)
        return DailyLiturgy.from_api_payload(payload)

    async def get_period(self, days: int) -> list[DailyLiturgy]:
        payload = await self.client.fetch_period(days)
        return [DailyLiturgy.from_api_payload(item) for item in payload]
