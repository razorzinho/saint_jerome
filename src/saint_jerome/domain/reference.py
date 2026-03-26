from __future__ import annotations

from saint_jerome.domain.models import Reference


def format_reference(reference: Reference) -> str:
    if reference.verse_start is None:
        return f"{reference.book_alias} {reference.chapter}"

    if reference.verse_end and reference.verse_end != reference.verse_start:
        return (
            f"{reference.book_alias} {reference.chapter}:"
            f"{reference.verse_start}-{reference.verse_end}"
        )

    return f"{reference.book_alias} {reference.chapter}:{reference.verse_start}"
