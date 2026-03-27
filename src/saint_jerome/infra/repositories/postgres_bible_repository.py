from __future__ import annotations

from dataclasses import dataclass

from saint_jerome.app.services.bible_service import BibleRepository
from saint_jerome.domain.models import Reference, Translation, Verse
from saint_jerome.domain.text_normalization import normalize_lookup_text
from saint_jerome.infra.database import PostgresPoolFactory


@dataclass(slots=True)
class PostgresBibleRepository(BibleRepository):
    pool_factory: PostgresPoolFactory

    async def get_translation(self, translation_id: str) -> Translation | None:
        pool = await self.pool_factory.get_pool()
        row = await pool.fetchrow(
            """
            SELECT id, name, language, canon
            FROM translations
            WHERE id = $1
            """,
            translation_id,
        )
        if row is None:
            return None

        return Translation(
            translation_id=row["id"],
            name=row["name"],
            language=row["language"],
            canon=row["canon"],
        )

    async def list_translations(self) -> list[Translation]:
        pool = await self.pool_factory.get_pool()
        rows = await pool.fetch(
            """
            SELECT id, name, language, canon
            FROM translations
            ORDER BY name
            """
        )
        return [
            Translation(
                translation_id=row["id"],
                name=row["name"],
                language=row["language"],
                canon=row["canon"],
            )
            for row in rows
        ]

    async def get_book_names(self, translation_id: str) -> list[str]:
        pool = await self.pool_factory.get_pool()
        rows = await pool.fetch(
            """
            SELECT DISTINCT ba.normalized_alias
            FROM book_aliases ba
            JOIN books b ON b.id = ba.book_id
            JOIN verses v ON v.book_id = b.id
            WHERE v.translation_id = $1
            ORDER BY ba.normalized_alias
            """,
            translation_id,
        )
        return [row["normalized_alias"] for row in rows]

    async def get_verses(self, reference: Reference, translation_id: str) -> list[Verse]:
        book_id = await self._resolve_book_id(reference.book_alias, translation_id)
        if book_id is None:
            return []

        params: list[object] = [translation_id, book_id, reference.chapter]
        query = """
            SELECT v.translation_id, b.code AS book_osis, b.name AS book_name,
                   v.chapter, v.verse, v.text
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.translation_id = $1
              AND v.book_id = $2
              AND v.chapter = $3
        """

        if reference.verse_start is not None:
            verse_end = reference.verse_end or reference.verse_start
            query += " AND v.verse BETWEEN $4 AND $5"
            params.extend([reference.verse_start, verse_end])

        query += " ORDER BY v.verse"
        pool = await self.pool_factory.get_pool()
        rows = await pool.fetch(query, *params)
        return [
            Verse(
                translation_id=row["translation_id"],
                book_osis=row["book_osis"],
                book_name=row["book_name"],
                chapter=row["chapter"],
                verse=row["verse"],
                text=row["text"],
            )
            for row in rows
        ]

    async def _resolve_book_id(self, book_alias: str, translation_id: str) -> int | None:
        normalized_alias = normalize_lookup_text(book_alias)
        pool = await self.pool_factory.get_pool()
        row = await pool.fetchrow(
            """
            SELECT b.id
            FROM book_aliases ba
            JOIN books b ON b.id = ba.book_id
            JOIN verses v ON v.book_id = b.id
            WHERE ba.normalized_alias = $1
              AND v.translation_id = $2
            ORDER BY b.canon_order
            LIMIT 1
            """,
            normalized_alias,
            translation_id,
        )
        return int(row["id"]) if row is not None else None
