from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from saint_jerome.domain.text_normalization import normalize_lookup_text

DEFAULT_BIBLIA_JSON_URL = "https://raw.githubusercontent.com/Dancrf/biblia-db/main/biblia.json"
DEFAULT_LISTA_LIVROS_URL = "https://raw.githubusercontent.com/Dancrf/biblia-db/main/listalivros.json"
DEFAULT_TRANSLATION_ID = "matos_soares_1956"
DEFAULT_TRANSLATION_NAME = "Padre Manuel de Matos Soares (1956)"
DEFAULT_LICENSE = "public-redistribution-claimed-by-source"

BOOK_TESTAMENT_CUTOFF = {
    "Mt",
}


@dataclass(slots=True, frozen=True)
class SourceBook:
    abbreviation: str
    chapter_count: int
    name: str
    testament: str
    canon_order: int
    chapters: list[dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa a Biblia do repositorio Dancrf/biblia-db para SQLite.",
    )
    parser.add_argument(
        "--db-path",
        default=str(Path("data") / "saint_jerome.db"),
        help="Caminho do banco SQLite de destino.",
    )
    parser.add_argument(
        "--source-file",
        help="Caminho local para o biblia.json. Se omitido, baixa do GitHub.",
    )
    parser.add_argument(
        "--books-file",
        help="Caminho local para o listalivros.json. Se omitido, baixa do GitHub.",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_BIBLIA_JSON_URL,
        help="URL do biblia.json.",
    )
    parser.add_argument(
        "--books-url",
        default=DEFAULT_LISTA_LIVROS_URL,
        help="URL do listalivros.json.",
    )
    parser.add_argument(
        "--translation-id",
        default=DEFAULT_TRANSLATION_ID,
        help="Identificador da traducao no banco.",
    )
    parser.add_argument(
        "--translation-name",
        default=DEFAULT_TRANSLATION_NAME,
        help="Nome da traducao no banco.",
    )
    parser.add_argument(
        "--language",
        default="pt-BR",
        help="Idioma da traducao.",
    )
    parser.add_argument(
        "--canon",
        default="catholic",
        help="Canon da traducao.",
    )
    parser.add_argument(
        "--license-label",
        default=DEFAULT_LICENSE,
        help="Rotulo de licenca salvo nos metadados da traducao.",
    )
    parser.add_argument(
        "--source-label",
        default="https://github.com/Dancrf/biblia-db",
        help="Origem textual salva na tabela translations.",
    )
    parser.add_argument(
        "--purge-translation",
        action="store_true",
        help="Remove os versos da traducao antes de reimportar.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        db_path = project_root / db_path

    bible_payload = _load_json(args.source_file, args.source_url)
    books_payload = _load_json(args.books_file, args.books_url)
    source_books = _build_source_books(bible_payload, books_payload)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        apply_sqlite_migration(connection, project_root / "migrations" / "sqlite" / "001_create_bible_schema.sql")
        import_translation(
            connection=connection,
            source_books=source_books,
            translation_id=args.translation_id,
            translation_name=args.translation_name,
            language=args.language,
            canon=args.canon,
            source_label=args.source_label,
            license_label=args.license_label,
            purge_translation=args.purge_translation,
        )
        connection.commit()
    finally:
        connection.close()

    print(f"Import completed into {db_path}")


def apply_sqlite_migration(connection: sqlite3.Connection, migration_file: Path) -> None:
    connection.executescript(migration_file.read_text(encoding="utf-8"))


def import_translation(
    *,
    connection: sqlite3.Connection,
    source_books: list[SourceBook],
    translation_id: str,
    translation_name: str,
    language: str,
    canon: str,
    source_label: str,
    license_label: str,
    purge_translation: bool,
) -> None:
    metadata_json = json.dumps(
        {
            "importer": "scripts/import_biblia_db.py",
            "source": source_label,
        },
        ensure_ascii=False,
    )
    connection.execute(
        """
        INSERT INTO translations (id, name, language, canon, source, license, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            language = excluded.language,
            canon = excluded.canon,
            source = excluded.source,
            license = excluded.license,
            metadata_json = excluded.metadata_json
        """,
        (
            translation_id,
            translation_name,
            language,
            canon,
            source_label,
            license_label,
            metadata_json,
        ),
    )

    if purge_translation:
        connection.execute(
            "DELETE FROM verses WHERE translation_id = ?",
            (translation_id,),
        )

    for book in source_books:
        connection.execute(
            """
            INSERT INTO books (code, abbreviation, name, testament, canon_order, chapter_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                abbreviation = excluded.abbreviation,
                name = excluded.name,
                testament = excluded.testament,
                canon_order = excluded.canon_order,
                chapter_count = excluded.chapter_count
            """,
            (
                book.abbreviation,
                book.abbreviation,
                book.name,
                book.testament,
                book.canon_order,
                book.chapter_count,
            ),
        )
        book_id = connection.execute(
            "SELECT id FROM books WHERE code = ?",
            (book.abbreviation,),
        ).fetchone()[0]

        _upsert_book_aliases(connection, book_id, book)
        _upsert_verses(connection, translation_id, book_id, book)


def _upsert_book_aliases(
    connection: sqlite3.Connection,
    book_id: int,
    book: SourceBook,
) -> None:
    aliases = {
        book.abbreviation,
        book.name,
        normalize_lookup_text(book.abbreviation),
        normalize_lookup_text(book.name),
    }
    aliases.update(_extra_aliases_for_book(book.abbreviation, book.name))

    for alias in aliases:
        if not alias:
            continue
        connection.execute(
            """
            INSERT INTO book_aliases (book_id, alias, normalized_alias)
            VALUES (?, ?, ?)
            ON CONFLICT(book_id, normalized_alias) DO UPDATE SET
                alias = excluded.alias
            """,
            (
                book_id,
                alias,
                normalize_lookup_text(alias),
            ),
        )


def _upsert_verses(
    connection: sqlite3.Connection,
    translation_id: str,
    book_id: int,
    book: SourceBook,
) -> None:
    for chapter in book.chapters:
        chapter_number = int(chapter["capitulo"])
        for verse in chapter.get("versiculos", []):
            connection.execute(
                """
                INSERT INTO verses (translation_id, book_id, chapter, verse, text)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(translation_id, book_id, chapter, verse) DO UPDATE SET
                    text = excluded.text
                """,
                (
                    translation_id,
                    book_id,
                    chapter_number,
                    int(verse["numero"]),
                    str(verse["texto"]).strip(),
                ),
            )


def _build_source_books(
    bible_payload: list[dict[str, Any]],
    books_payload: list[dict[str, Any]],
) -> list[SourceBook]:
    if len(bible_payload) != len(books_payload):
        raise ValueError(
            "O biblia.json e o listalivros.json nao possuem a mesma quantidade de livros."
        )

    source_books: list[SourceBook] = []
    new_testament_started = False
    for index, (book_data, metadata) in enumerate(zip(bible_payload, books_payload, strict=True), start=1):
        abbreviation = str(metadata["livro"]).strip()
        if abbreviation in BOOK_TESTAMENT_CUTOFF:
            new_testament_started = True

        source_books.append(
            SourceBook(
                abbreviation=abbreviation,
                chapter_count=int(metadata["quantidadeCap"]),
                name=str(book_data["livro"]).strip(),
                testament="new" if new_testament_started else "old",
                canon_order=index,
                chapters=list(book_data.get("capitulos", [])),
            )
        )
    return source_books


def _load_json(local_path: str | None, remote_url: str) -> Any:
    if local_path:
        return json.loads(Path(local_path).read_text(encoding="utf-8"))

    with urlopen(remote_url, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _extra_aliases_for_book(abbreviation: str, name: str) -> set[str]:
    normalized_name = normalize_lookup_text(name)
    aliases = {normalized_name}

    custom_aliases = {
        "Gn": {"gen", "genesis"},
        "Ex": {"exodo"},
        "Lv": {"lev", "levitico"},
        "Nm": {"numeros"},
        "Dt": {"deut", "deuteronomio"},
        "Js": {"josue"},
        "Ju": {"juizes", "jdz"},
        "Rt": {"rute"},
        "1Sm": {"1 samuel", "i samuel"},
        "2Sm": {"2 samuel", "ii samuel"},
        "1Rs": {"1 reis", "i reis"},
        "2Rs": {"2 reis", "ii reis"},
        "1Pa": {"1 cronicas", "i cronicas"},
        "2Pa": {"2 cronicas", "ii cronicas"},
        "Esd": {"esdras"},
        "Ne": {"neemias"},
        "Tob": {"tobias", "tb"},
        "Jdi": {"judite", "jdt"},
        "Est": {"ester"},
        "Job": {"jo"},
        "Ps": {"salmo", "salmos", "sl"},
        "Pv": {"proverbios", "prov"},
        "Ees": {"eclesiastes", "ec"},
        "Cc": {"canticos", "cantares", "cantico dos canticos"},
        "Sa": {"sabedoria", "sab"},
        "Eus": {"eclesiastico", "siracida", "siracides", "sir"},
        "Is": {"isaias"},
        "Je": {"jeremias"},
        "Lm": {"lamentacoes"},
        "Ba": {"baruc"},
        "Ez": {"ezequiel"},
        "Dn": {"daniel"},
        "Os": {"oseias"},
        "Jl": {"joel"},
        "Am": {"amos"},
        "Ab": {"abdias"},
        "Jn": {"jonas"},
        "Mic": {"miqueias", "mq"},
        "Na": {"naum"},
        "Hc": {"habacuc"},
        "So": {"sofonias"},
        "Ag": {"ageu"},
        "Zc": {"zacarias"},
        "Ml": {"malaquias"},
        "1Ma": {"1 macabeus", "i macabeus"},
        "2Ma": {"2 macabeus", "ii macabeus"},
        "Mt": {"mateus", "mat"},
        "Mc": {"marcos"},
        "Lc": {"lucas", "luc"},
        "Jo": {"joao", "john", "jn"},
        "Act": {"atos", "atos dos apostolos", "at"},
        "Rm": {"romanos"},
        "1Co": {"1 corintios", "i corintios"},
        "2Co": {"2 corintios", "ii corintios"},
        "Gl": {"galatas"},
        "Ef": {"efesios"},
        "Fp": {"filipenses", "fl"},
        "Cl": {"colossenses", "col"},
        "1Ts": {"1 tessalonicenses", "i tessalonicenses"},
        "2Ts": {"2 tessalonicenses", "ii tessalonicenses"},
        "1Tm": {"1 timoteo", "i timoteo"},
        "2Tm": {"2 timoteo", "ii timoteo"},
        "Tt": {"tito"},
        "Fm": {"filemon", "flm"},
        "Hb": {"hebreus"},
        "Tg": {"tiago"},
        "1Pe": {"1 pedro", "i pedro"},
        "2Pe": {"2 pedro", "ii pedro"},
        "1Jo": {"1 joao", "i joao"},
        "2Jo": {"2 joao", "ii joao"},
        "3Jo": {"3 joao", "iii joao"},
        "Jda": {"judas"},
        "Ap": {"apocalipse", "rev"},
    }
    aliases.update(custom_aliases.get(abbreviation, set()))
    return aliases


if __name__ == "__main__":
    main()
