from __future__ import annotations

import re
from dataclasses import dataclass

from saint_jerome.domain.models import Reference
from saint_jerome.domain.text_normalization import normalize_lookup_text

REFERENCE_PATTERN = re.compile(
    r"^\s*(?P<book>[1-3]?\s*[A-Za-zÀ-ÿ.]+(?:\s+[A-Za-zÀ-ÿ.]+)*)\s+"
    r"(?P<chapter>\d+)"
    r"(?:\:(?P<verse_start>\d+)(?:-(?P<verse_end>\d+))?)?\s*"
    r"(?P<translation>[A-Za-z0-9_-]+)?\s*$"
)

INLINE_PATTERN = re.compile(
    r"(?i)\b([1-3]?\s*[a-záéíóúâêîôûãõç]+(?:\s+[a-záéíóúâêîôûãõç]+)*)\s+(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\b"
)


class ReferenceParserError(ValueError):
    """Raised when a reference cannot be parsed."""


@dataclass(slots=True)
class ReferenceParser:
    def parse(self, raw_reference: str) -> Reference:
        match = REFERENCE_PATTERN.match(raw_reference)
        if not match:
            raise ReferenceParserError(f"Referência inválida ou não reconhecida: {raw_reference!r}")

        groups = match.groupdict()
        return Reference(
            book_alias=self._normalize_book(groups["book"]),
            chapter=int(groups["chapter"]),
            verse_start=self._to_int(groups["verse_start"]),
            verse_end=self._to_int(groups["verse_end"]),
            translation=groups["translation"].lower() if groups["translation"] else None,
        )

    def extract_all(self, text: str) -> list[Reference]:
        references = []
        for match in INLINE_PATTERN.finditer(text):
            book, chapter, verse_start, verse_end = match.groups()
            references.append(
                Reference(
                    book_alias=self._normalize_book(book),
                    chapter=int(chapter),
                    verse_start=self._to_int(verse_start),
                    verse_end=self._to_int(verse_end),
                    translation=None,
                )
            )
        return references

    @staticmethod
    def _normalize_book(book: str) -> str:
        return normalize_lookup_text(book.replace(".", " "))

    @staticmethod
    def _to_int(value: str | None) -> int | None:
        return int(value) if value is not None else None
