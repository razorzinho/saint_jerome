from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Reference:
    book_alias: str
    chapter: int
    verse_start: int | None = None
    verse_end: int | None = None
    translation: str | None = None


@dataclass(slots=True, frozen=True)
class Verse:
    translation_id: str
    book_osis: str
    book_name: str
    chapter: int
    verse: int
    text: str


@dataclass(slots=True, frozen=True)
class Book:
    osis: str
    name: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class Translation:
    translation_id: str
    name: str
    language: str
    canon: str
