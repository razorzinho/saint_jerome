from __future__ import annotations

import asyncio
from pathlib import Path

from saint_jerome.app.services.bible_service import BibleService
from saint_jerome.bot.client import build_container
from saint_jerome.bot.commands.versiculo import build_verse_embeds
from saint_jerome.config.settings import Settings
from saint_jerome.infra.loaders.json_loader import load_json_file
from saint_jerome.infra.repositories.memory_repository import MemoryBibleRepository


async def main() -> None:
    settings = Settings()
    payload = load_json_file(settings.sample_data_file)
    repository = MemoryBibleRepository(payload)
    service = BibleService(
        repository=repository,
        default_translation=settings.default_translation,
    )
    container = build_container(service)

    print("\n--- TESTE DE ESCUTA PASSIVA ---")
    mensagem_teste = "Estava aqui lendo João 6:53-61 e também vendo sobre João 8:58, e realmente, é bastante difícil negar que Jesus é Deus. Salmo 23:1"
    references = container.parser.extract_all(mensagem_teste)
    print(f"Mensagem: '{mensagem_teste}'")
    for ref in references:
        try:
            verses = await container.bible_service.get_passage(ref)
            nome = verses[0].book_name
            titulo = f"{nome} {ref.chapter}:{ref.verse_start}"
            if ref.verse_end:
                 titulo += f"-{ref.verse_end}"
            print(f" -> Encontrado: {titulo}")
        except Exception as e:
            print(f" -> Ignorado silenciosamente: {ref.book_alias} (Erro: {e})")
    print("-" * 40)

    for raw_reference in ("joao 3:16", "jaoa 3:16", "salmo 23", "tobias 12:8"):
        print(f"\nBusca: {raw_reference}")
        try:
            embeds = await build_verse_embeds(container, raw_reference)
            for embed in embeds:
                print(f"[{embed.title}]")
                print(embed.description[:50] + "...")
        except Exception as e:
            print(f"Erro: {e}")
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())
