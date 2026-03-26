from __future__ import annotations

import discord

from saint_jerome.bot.client import BotContainer
from saint_jerome.domain.models import Reference


async def build_verse_embeds(
    container: BotContainer, 
    raw_reference: str | None = None, 
    parsed_reference: Reference | None = None
) -> list[discord.Embed]:
    reference = parsed_reference or container.parser.parse(raw_reference)
    verses = await container.bible_service.get_passage(reference)

    book_name = verses[0].book_name
    chapter = reference.chapter
    translation_id = verses[0].translation_id.upper()

    if reference.verse_start is None:
        title = f"{book_name} {chapter} ({translation_id})"
    elif reference.verse_end and reference.verse_end != reference.verse_start:
        title = f"{book_name} {chapter}:{reference.verse_start}-{reference.verse_end} ({translation_id})"
    else:
        title = f"{book_name} {chapter}:{reference.verse_start} ({translation_id})"

    embeds = []
    current_description = ""
    color = discord.Color.gold()

    for verse in verses:
        verse_text = f"**{verse.verse}** {verse.text}\n"
        if len(current_description) + len(verse_text) > 3900:
            embed = discord.Embed(title=title, description=current_description.strip(), color=color)
            embeds.append(embed)
            current_description = verse_text
        else:
            current_description += verse_text

    if current_description:
        embeds.append(discord.Embed(title=title, description=current_description.strip(), color=color))

    if len(embeds) > 1:
        for i, embed in enumerate(embeds):
            embed.set_footer(text=f"Página {i + 1} de {len(embeds)}")

    return embeds
