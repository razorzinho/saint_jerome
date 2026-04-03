from __future__ import annotations

import re

import discord

from saint_jerome.domain.liturgy import DailyLiturgy, ReadingOption

EMBED_DESCRIPTION_LIMIT = 3900
EMBED_TOTAL_CHAR_LIMIT = 6000

SECTION_LABELS = {
    "primeiraLeitura": "Primeira Leitura",
    "salmo": "Salmo",
    "segundaLeitura": "Segunda Leitura",
    "evangelho": "Evangelho",
    "extras": "Leituras Extras",
}

PRAYER_LABELS = {
    "coleta": "Coleta",
    "oferendas": "Oferendas",
    "comunhao": "Comunhão",
}


def build_liturgy_embeds(
    liturgy: DailyLiturgy,
    *,
    include_prayers: bool = True,
    include_antiphons: bool = True,
    include_extras: bool = True,
) -> list[discord.Embed]:
    color = _map_liturgical_color(liturgy.color)
    embeds: list[discord.Embed] = [
        discord.Embed(
            title=liturgy.liturgy or "Liturgia Diária",
            description=f"**Data:** {liturgy.date}\n**Cor litúrgica:** {liturgy.color or 'Não informada'}",
            color=color,
        )
    ]

    for section_key in _ordered_reading_keys(liturgy.readings):
        section_label = SECTION_LABELS.get(section_key, _prettify_key(section_key))
        options = liturgy.readings.get(section_key, ())
        for index, option in enumerate(options, start=1):
            option_label = (
                f"{section_label} {index}/{len(options)}" if len(options) > 1 else section_label
            )
            embeds.extend(_build_reading_embeds(option_label, option, color))

    if include_prayers:
        for key, text in liturgy.prayers.items():
            label = PRAYER_LABELS.get(key, _prettify_key(key))
            embeds.extend(
                _split_into_embeds(
                    title=f"Orações • {label}",
                    body=text,
                    color=color,
                )
            )

    if include_antiphons:
        for key, text in liturgy.antiphons.items():
            embeds.extend(
                _split_into_embeds(
                    title=f"Antífonas • {_prettify_key(key)}",
                    body=text,
                    color=color,
                )
            )

    if include_extras:
        for extra in liturgy.prayer_extras:
            embeds.extend(
                _split_into_embeds(
                    title=f"Extras • {extra.title}",
                    body=extra.text,
                    color=color,
                )
            )

    _set_page_footers(embeds)
    return embeds


def build_liturgy_period_embeds(liturgies: list[DailyLiturgy]) -> list[discord.Embed]:
    color = discord.Color.blurple()
    embeds: list[discord.Embed] = []
    current_embed = discord.Embed(
        title="Liturgia Diária • Próximos dias",
        color=color,
    )

    for item in liturgies:
        lines = [f"Cor: {item.color or 'Não informada'}"]
        for key in _ordered_reading_keys(item.readings):
            first_option = item.readings[key][0]
            label = SECTION_LABELS.get(key, _prettify_key(key))
            lines.append(f"{label}: {first_option.reference}")

        value = "\n".join(lines)
        field_name = f"{item.date} • {item.liturgy}"
        if (
            len(current_embed.fields) >= 8
            or get_embed_character_count(current_embed) + len(field_name) + len(value[:1024]) > EMBED_TOTAL_CHAR_LIMIT
        ):
            embeds.append(current_embed)
            current_embed = discord.Embed(
                title="Liturgia Diária • Próximos dias",
                color=color,
            )

        current_embed.add_field(
            name=field_name,
            value=value[:1024],
            inline=False,
        )

    if current_embed.fields:
        embeds.append(current_embed)

    _set_page_footers(embeds)
    return embeds


def _build_reading_embeds(label: str, option: ReadingOption, color: discord.Color) -> list[discord.Embed]:
    header_lines = []
    if option.reference:
        header_lines.append(f"**Referência:** {option.reference}")
    if option.title:
        header_lines.append(f"**Título:** {option.title}")
    if option.refrain:
        header_lines.append(f"**Refrão:** {option.refrain}")

    header = "\n".join(header_lines).strip()
    body = option.text
    if header:
        body = f"{header}\n\n{body}" if body else header

    return _split_into_embeds(title=f"Leituras • {label}", body=body, color=color)


def _split_into_embeds(*, title: str, body: str, color: discord.Color) -> list[discord.Embed]:
    chunks = _chunk_text(body.strip(), max_length=EMBED_DESCRIPTION_LIMIT)
    if not chunks:
        chunks = ["(Sem conteúdo)"]

    embeds: list[discord.Embed] = []
    for index, chunk in enumerate(chunks, start=1):
        embed_title = title if len(chunks) == 1 else f"{title} ({index}/{len(chunks)})"
        embeds.append(discord.Embed(title=embed_title, description=chunk, color=color))
    return embeds


def _chunk_text(text: str, *, max_length: int) -> list[str]:
    if not text:
        return []

    normalized = text.replace("\r\n", "\n").strip()
    paragraphs = [paragraph.strip() for paragraph in normalized.split("\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_length:
            for sentence_chunk in _force_split(paragraph, max_length=max_length):
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(sentence_chunk)
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_length:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def _force_split(text: str, *, max_length: int) -> list[str]:
    pieces: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_length:
            pieces.append(remaining)
            break

        split_at = remaining.rfind(" ", 0, max_length)
        if split_at <= 0:
            split_at = max_length

        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    return [piece for piece in pieces if piece]


def _ordered_reading_keys(readings: dict[str, tuple[ReadingOption, ...]]) -> list[str]:
    preferred_order = ["primeiraLeitura", "salmo", "segundaLeitura", "evangelho", "extras"]
    ordered = [key for key in preferred_order if key in readings]
    ordered.extend(key for key in readings if key not in ordered)
    return ordered


def _map_liturgical_color(color_name: str) -> discord.Color:
    normalized = color_name.casefold()
    if normalized == "verde":
        return discord.Color.green()
    if normalized == "vermelho":
        return discord.Color.red()
    if normalized == "roxo":
        return discord.Color.purple()
    if normalized == "rosa":
        return discord.Color.from_rgb(231, 84, 128)
    if normalized == "branco":
        return discord.Color.light_grey()
    return discord.Color.gold()


def _set_page_footers(embeds: list[discord.Embed]) -> None:
    if len(embeds) <= 1:
        return

    for index, embed in enumerate(embeds, start=1):
        embed.set_footer(text=f"Página {index} de {len(embeds)}")


def get_embed_character_count(embed: discord.Embed) -> int:
    total = len(embed.title or "") + len(embed.description or "")
    total += len(embed.footer.text) if embed.footer else 0

    if embed.author:
        total += len(embed.author.name or "")

    for field in embed.fields:
        total += len(field.name) + len(field.value)

    return total


def _prettify_key(value: str) -> str:
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", value).replace("_", " ")
    words = spaced.split()
    return " ".join(word.capitalize() for word in words)
