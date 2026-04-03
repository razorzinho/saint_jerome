from __future__ import annotations

import re
from dataclasses import dataclass

from saint_jerome.domain.models import Reference
from saint_jerome.domain.text_normalization import normalize_lookup_text

REFERENCE_PATTERN = re.compile(
    r"^\s*(?P<book>[1-3]?\s*[A-Za-zÀ-ÿ.]+(?:\s+[A-Za-zÀ-ÿ.]+)*)\s+"
    r"(?P<chapter>\d+)"
    r"(?:\s*[:.,]\s*(?P<verse_start>\d+)(?:\s*[-–—]\s*(?P<verse_end>\d+))?)?\s*"
    r"(?P<translation>[A-Za-z0-9_-]+)?\s*$"
)

INLINE_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9])"
    r"(?P<book>[1-3]?\s*[A-Za-zÀ-ÿ.]+(?:\s+[A-Za-zÀ-ÿ.]+){0,3})"
    r"\s+"
    r"(?P<chapter>\d+)"
    r"(?:\s*[:.,]\s*(?P<verse_start>\d+)(?:\s*[-–—]\s*(?P<verse_end>\d+))?)?"
    r"(?=$|[\s,.;:!?()\[\]{}\"'])"
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
        references: list[Reference] = []
        seen: set[tuple[str, int, int | None, int | None]] = set()

        for match in INLINE_PATTERN.finditer(text):
            groups = match.groupdict()
            reference = Reference(
                book_alias=self._normalize_book(groups["book"]),
                chapter=int(groups["chapter"]),
                verse_start=self._to_int(groups["verse_start"]),
                verse_end=self._to_int(groups["verse_end"]),
                translation=None,
            )
            key = (
                reference.book_alias,
                reference.chapter,
                reference.verse_start,
                reference.verse_end,
            )
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
        return references

    @staticmethod
    def _normalize_book(book: str) -> str:
        return normalize_lookup_text(book.replace(".", " "))

    @staticmethod
    def _to_int(value: str | None) -> int | None:
        return int(value) if value is not None else None
