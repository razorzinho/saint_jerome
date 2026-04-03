from __future__ import annotations

import discord
import pytest

from saint_jerome.bot.cogs.liturgy_cog import LiturgyCog
from saint_jerome.bot.commands.liturgia import (
    build_liturgy_period_embeds,
    get_embed_character_count,
)
from saint_jerome.domain.liturgy import DailyLiturgy, ReadingOption


def test_build_liturgy_period_embeds_respects_embed_character_limit() -> None:
    liturgies = [
        DailyLiturgy(
            date=f"2026-04-{day:02d}",
            liturgy=f"Celebração {day}",
            color="Branco",
            prayers={},
            readings={
                "primeiraLeitura": (
                    ReadingOption(
                        section_key="primeiraLeitura",
                        reference="Isaías 1,1-10",
                        title="Leitura longa",
                        text="texto",
                    ),
                )
            },
        )
        for day in range(1, 8)
    ]

    embeds = build_liturgy_period_embeds(liturgies)

    assert embeds
    assert all(get_embed_character_count(embed) <= 6000 for embed in embeds)


@pytest.mark.asyncio
async def test_send_embeds_splits_messages_by_total_character_limit() -> None:
    class FakeDestination:
        def __init__(self) -> None:
            self.payloads: list[list[discord.Embed]] = []

        async def send(self, *, embeds: list[discord.Embed]) -> None:
            self.payloads.append(embeds)

    destination = FakeDestination()
    embeds = [
        discord.Embed(title=f"Embed {index}", description="x" * 3900)
        for index in range(3)
    ]

    cog = object.__new__(LiturgyCog)
    await LiturgyCog._send_embeds(cog, destination, embeds)

    assert len(destination.payloads) == 3
    assert all(len(payload) == 1 for payload in destination.payloads)
