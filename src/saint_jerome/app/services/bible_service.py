from __future__ import annotations

import difflib
from dataclasses import dataclass

from saint_jerome.domain.models import Reference, Translation, Verse


class BibleRepository:
    async def get_translation(self, translation_id: str) -> Translation | None:
        raise NotImplementedError

    async def list_translations(self) -> list[Translation]:
        raise NotImplementedError

    async def get_book_names(self, translation_id: str) -> list[str]:
        raise NotImplementedError

    async def get_verses(self, reference: Reference, translation_id: str) -> list[Verse]:
        raise NotImplementedError


@dataclass(slots=True)
class BibleService:
    repository: BibleRepository
    default_translation: str

    async def list_translations(self) -> list[Translation]:
        return await self.repository.list_translations()

    async def get_passage(self, reference: Reference) -> list[Verse]:
        translation_id = reference.translation or self.default_translation
        translation = await self.repository.get_translation(translation_id)
        if translation is None:
            raise LookupError(f"Tradução desconhecida ou indisponível: '{translation_id}'")

        verses = await self.repository.get_verses(reference, translation_id)
        if not verses:
            available_books = await self.repository.get_book_names(translation_id)
            matches = difflib.get_close_matches(reference.book_alias, available_books, n=1, cutoff=0.5)
            
            if matches:
                suggestion = matches[0].title()
                raise LookupError(f"Livro não encontrado. Você quis dizer **'{suggestion}'**?")
            else:
                raise LookupError("Passagem ou livro não encontrados nesta tradução.")
        
        return verses
