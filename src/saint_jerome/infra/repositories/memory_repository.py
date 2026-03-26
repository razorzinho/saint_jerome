from __future__ import annotations

from dataclasses import dataclass

from saint_jerome.app.services.bible_service import BibleRepository
from saint_jerome.domain.models import Reference, Translation, Verse
from saint_jerome.domain.text_normalization import normalize_lookup_text


@dataclass(slots=True)
class MemoryBibleRepository(BibleRepository):
    payload: dict

    async def get_translation(self, translation_id: str) -> Translation | None:
        for item in self.payload.get("translations", []):
            if item["id"] == translation_id:
                return Translation(
                    translation_id=item["id"],
                    name=item["name"],
                    language=item["language"],
                    canon=item["canon"],
                )
        return None

    async def list_translations(self) -> list[Translation]:
        items = []
        for item in self.payload.get("translations", []):
            items.append(
                Translation(
                    translation_id=item["id"],
                    name=item["name"],
                    language=item["language"],
                    canon=item["canon"],
                )
            )
        return items

    async def get_book_names(self, translation_id: str) -> list[str]:
        translation = self._find_translation(translation_id)
        if not translation:
            return []
            
        names = []
        for book in translation.get("books", []):
            names.append(normalize_lookup_text(book["name"]))
            for alias in book.get("aliases", []):
                names.append(normalize_lookup_text(alias))
        return names

    async def get_verses(self, reference: Reference, translation_id: str) -> list[Verse]:
        translation = self._find_translation(translation_id)
        if translation is None:
            return []

        for book in translation.get("books", []):
            aliases = {normalize_lookup_text(alias) for alias in book.get("aliases", [])}
            aliases.add(normalize_lookup_text(book["name"]))
            if reference.book_alias not in aliases:
                continue

            chapter = book.get("chapters", {}).get(str(reference.chapter))
            if chapter is None:
                return []

            if reference.verse_start is None:
                return self._chapter_to_verses(book, chapter, translation_id, reference.chapter)

            end = reference.verse_end or reference.verse_start
            verses = []
            for verse_number in range(reference.verse_start, end + 1):
                verse_text = chapter.get(str(verse_number))
                if verse_text is None:
                    continue
                verses.append(
                    Verse(
                        translation_id=translation_id,
                        book_osis=book["osis"],
                        book_name=book["name"],
                        chapter=reference.chapter,
                        verse=verse_number,
                        text=verse_text,
                    )
                )
            return verses

        return []

    def _find_translation(self, translation_id: str) -> dict | None:
        for item in self.payload.get("translations", []):
            if item["id"] == translation_id:
                return item
        return None

    @staticmethod
    def _chapter_to_verses(
        book: dict,
        chapter: dict,
        translation_id: str,
        chapter_number: int,
    ) -> list[Verse]:
        verses = []
        for verse_number, text in sorted(chapter.items(), key=lambda item: int(item[0])):
            verses.append(
                Verse(
                    translation_id=translation_id,
                    book_osis=book["osis"],
                    book_name=book["name"],
                    chapter=chapter_number,
                    verse=int(verse_number),
                    text=text,
                )
            )
        return verses
