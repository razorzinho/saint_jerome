from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.import_biblia_db import (
    BOOK_METADATA,
    SourceBook,
    _build_source_books,
    apply_sqlite_migration,
    import_translation,
)


def test_import_biblia_db_populates_normalized_schema(tmp_path: Path) -> None:
    source_books = [
        SourceBook(
            abbreviation="Gn",
            chapter_count=1,
            name="Gênesis",
            testament="old",
            canon_order=1,
            chapters=[
                {
                    "capitulo": 1,
                    "versiculos": [
                        {"numero": 1, "texto": "No princípio criou Deus o céu e a terra."},
                        {"numero": 2, "texto": "A terra, porém, estava informe e vazia."},
                    ],
                }
            ],
        ),
        SourceBook(
            abbreviation="Mt",
            chapter_count=1,
            name="Evangelho segundo S. Mateus",
            testament="new",
            canon_order=47,
            chapters=[
                {
                    "capitulo": 1,
                    "versiculos": [
                        {"numero": 1, "texto": "Livro da genealogia de Jesus Cristo."},
                    ],
                }
            ],
        ),
    ]
    db_path = tmp_path / "test.db"
    connection = sqlite3.connect(db_path)
    try:
        migration_file = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "sqlite"
            / "001_create_bible_schema.sql"
        )
        apply_sqlite_migration(connection, migration_file)
        import_translation(
            connection=connection,
            source_books=source_books,
            translation_id="matos_soares_1956",
            translation_name="Matos Soares",
            language="pt-BR",
            canon="catholic",
            source_label="test",
            license_label="test",
            purge_translation=False,
        )
        connection.commit()

        translation_count = connection.execute(
            "SELECT COUNT(*) FROM translations"
        ).fetchone()[0]
        verse_count = connection.execute(
            "SELECT COUNT(*) FROM verses"
        ).fetchone()[0]
        alias_exists = connection.execute(
            """
            SELECT COUNT(*)
            FROM book_aliases ba
            JOIN books b ON b.id = ba.book_id
            WHERE b.code = 'Gn' AND ba.normalized_alias = 'genesis'
            """
        ).fetchone()[0]

        assert translation_count == 1
        assert verse_count == 3
        assert alias_exists == 1
    finally:
        connection.close()


def test_build_source_books_uses_stable_metadata_instead_of_positional_codes() -> None:
    bible_payload = []
    books_payload = []

    for metadata in BOOK_METADATA:
        bible_payload.append(
            {
                "livro": metadata.expected_name,
                "capitulos": [
                    {
                        "capitulo": 1,
                        "versiculos": [
                            {
                                "numero": 1,
                                "texto": f"Texto de teste para {metadata.code}.",
                            }
                        ],
                    }
                ],
            }
        )
        books_payload.append({"livro": metadata.code, "quantidadeCap": 1})

    source_books = _build_source_books(bible_payload, books_payload)

    assert source_books[19].abbreviation == "1Ma"
    assert source_books[19].name == "Livro Primeiro dos Macabeus"
    assert source_books[20].abbreviation == "2Ma"
    assert source_books[21].abbreviation == "Job"
    assert source_books[22].abbreviation == "Ps"
    assert source_books[27].abbreviation == "Eus"
    assert source_books[49].abbreviation == "Jo"
