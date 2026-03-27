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

@dataclass(slots=True, frozen=True)
class SourceBook:
    abbreviation: str
    chapter_count: int
    name: str
    testament: str
    canon_order: int
    chapters: list[dict[str, Any]]


@dataclass(slots=True, frozen=True)
class CanonicalBookMetadata:
    code: str
    expected_name: str
    testament: str
    canon_order: int


BOOK_METADATA: tuple[CanonicalBookMetadata, ...] = (
    CanonicalBookMetadata("Gn", "Gênesis", "old", 1),
    CanonicalBookMetadata("Ex", "Êxodo", "old", 2),
    CanonicalBookMetadata("Lv", "Levítico", "old", 3),
    CanonicalBookMetadata("Nm", "Números", "old", 4),
    CanonicalBookMetadata("Dt", "Deuteronómio", "old", 5),
    CanonicalBookMetadata("Js", "Livro de Josué", "old", 6),
    CanonicalBookMetadata("Ju", "Livro dos Juízes", "old", 7),
    CanonicalBookMetadata("Rt", "Livro de Rute", "old", 8),
    CanonicalBookMetadata("1Sm", "Livro Primeiro de Samuel", "old", 9),
    CanonicalBookMetadata("2Sm", "Livro Segundo de Samuel", "old", 10),
    CanonicalBookMetadata("1Rs", "Livro Primeiro dos Reis", "old", 11),
    CanonicalBookMetadata("2Rs", "Livro Segundo dos Reis", "old", 12),
    CanonicalBookMetadata("1Pa", "Livro Primeiro das Crónicas", "old", 13),
    CanonicalBookMetadata("2Pa", "Livro Segundo das Crónicas", "old", 14),
    CanonicalBookMetadata("Esd", "Livro de Esdras", "old", 15),
    CanonicalBookMetadata("Ne", "Livro de Neemias", "old", 16),
    CanonicalBookMetadata("Tob", "Livro de Tobias", "old", 17),
    CanonicalBookMetadata("Jdi", "Livro de Judit", "old", 18),
    CanonicalBookMetadata("Est", "Livro de Ester", "old", 19),
    CanonicalBookMetadata("1Ma", "Livro Primeiro dos Macabeus", "old", 20),
    CanonicalBookMetadata("2Ma", "Livro Segundo dos Macabeus", "old", 21),
    CanonicalBookMetadata("Job", "Livro de Job (Jó)", "old", 22),
    CanonicalBookMetadata("Ps", "Salmos", "old", 23),
    CanonicalBookMetadata("Pv", "Livro dos Provérbios", "old", 24),
    CanonicalBookMetadata("Ees", "Livro do Eclesiaste", "old", 25),
    CanonicalBookMetadata("Cc", "Cânticos dos Cânticos", "old", 26),
    CanonicalBookMetadata("Sa", "Livro da Sabedoria", "old", 27),
    CanonicalBookMetadata("Eus", "Eclesiástico", "old", 28),
    CanonicalBookMetadata("Is", "Profecia de Isaías", "old", 29),
    CanonicalBookMetadata("Je", "Profecia de Jeremias", "old", 30),
    CanonicalBookMetadata("Lm", "Trenos ou Lamentações de Jeremias", "old", 31),
    CanonicalBookMetadata("Ba", "Profecia de Baruch", "old", 32),
    CanonicalBookMetadata("Ez", "Profecia de Ezequiel", "old", 33),
    CanonicalBookMetadata("Dn", "Profecia de Daniel", "old", 34),
    CanonicalBookMetadata("Os", "Oseias", "old", 35),
    CanonicalBookMetadata("Jl", "Profecia de Joel", "old", 36),
    CanonicalBookMetadata("Am", "Profecia de Amós", "old", 37),
    CanonicalBookMetadata("Ab", "Profecia de Abdias", "old", 38),
    CanonicalBookMetadata("Jn", "Profecia de Jonas", "old", 39),
    CanonicalBookMetadata("Mic", "Profecia de Miqueias", "old", 40),
    CanonicalBookMetadata("Na", "Profecia de Naum", "old", 41),
    CanonicalBookMetadata("Hc", "Profecia de Habucuc", "old", 42),
    CanonicalBookMetadata("So", "Profecia de Sofonias", "old", 43),
    CanonicalBookMetadata("Ag", "Profecia de Ageu", "old", 44),
    CanonicalBookMetadata("Zc", "Profecia de Zacarias", "old", 45),
    CanonicalBookMetadata("Ml", "Profecia de Malaquias", "old", 46),
    CanonicalBookMetadata("Mt", "Evangelho segundo S. Mateus", "new", 47),
    CanonicalBookMetadata("Mc", "Evangelho segundo S. Marcos", "new", 48),
    CanonicalBookMetadata("Lc", "Evangelho segundo S. Lucas", "new", 49),
    CanonicalBookMetadata("Jo", "Evangelho segundo S. João", "new", 50),
    CanonicalBookMetadata("Act", "Atos dos Apóstolos", "new", 51),
    CanonicalBookMetadata("Rm", "Epístola aos Romanos", "new", 52),
    CanonicalBookMetadata("1Co", "Primeira Epístola aos Coríntios", "new", 53),
    CanonicalBookMetadata("2Co", "Segunda Epístola aos Coríntios", "new", 54),
    CanonicalBookMetadata("Gl", "Epístola aos Galatas", "new", 55),
    CanonicalBookMetadata("Ef", "Epístola aos Efésios", "new", 56),
    CanonicalBookMetadata("Fp", "Epístola aos Filipenses", "new", 57),
    CanonicalBookMetadata("Cl", "Epístola aos Colossenses", "new", 58),
    CanonicalBookMetadata("1Ts", "Primeira Epístola aos Tessalonicenses", "new", 59),
    CanonicalBookMetadata("2Ts", "Segunda Epístola aos Tessalonicenses", "new", 60),
    CanonicalBookMetadata("1Tm", "Primeira Epístola a Timóteo", "new", 61),
    CanonicalBookMetadata("2Tm", "Segunda Epístola a Timóteo", "new", 62),
    CanonicalBookMetadata("Tt", "Epístola a Títo", "new", 63),
    CanonicalBookMetadata("Fm", "Epístola a Filémon", "new", 64),
    CanonicalBookMetadata("Hb", "Epístola aos Hebreus", "new", 65),
    CanonicalBookMetadata("Tg", "Epístola de S. Tiago", "new", 66),
    CanonicalBookMetadata("1Pe", "Primeira Epístola de S. Pedro", "new", 67),
    CanonicalBookMetadata("2Pe", "Segunda Epístola de S. Pedro", "new", 68),
    CanonicalBookMetadata("1Jo", "Primeira Epístola de S. João", "new", 69),
    CanonicalBookMetadata("2Jo", "Segunda Epístolas de S. João", "new", 70),
    CanonicalBookMetadata("3Jo", "Terceira Epístolas de S. João", "new", 71),
    CanonicalBookMetadata("Jda", "Epístola de S. Judas", "new", 72),
    CanonicalBookMetadata("Ap", "Apocalipse de S. João", "new", 73),
)


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

        connection.execute(
            "DELETE FROM book_aliases WHERE book_id = ?",
            (book_id,),
        )
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
    if len(bible_payload) != len(BOOK_METADATA):
        raise ValueError(
            "O biblia.json nao possui a quantidade esperada de livros."
        )

    chapter_count_by_code = {
        str(item["livro"]).strip(): int(item["quantidadeCap"])
        for item in books_payload
    }

    source_books: list[SourceBook] = []
    for book_data, metadata in zip(bible_payload, BOOK_METADATA, strict=True):
        source_name = str(book_data["livro"]).strip()
        normalized_source_name = normalize_lookup_text(source_name)
        normalized_expected_name = normalize_lookup_text(metadata.expected_name)
        if normalized_source_name != normalized_expected_name:
            raise ValueError(
                "A ordem ou o nome dos livros em biblia.json mudou. "
                f"Esperado: {metadata.expected_name!r}. Recebido: {source_name!r}."
            )

        chapter_count = chapter_count_by_code.get(metadata.code)
        if chapter_count is None:
            raise ValueError(
                f"O listalivros.json nao possui o codigo esperado: {metadata.code!r}."
            )

        actual_chapter_count = len(book_data.get("capitulos", []))
        if actual_chapter_count != chapter_count:
            raise ValueError(
                f"Quantidade de capitulos inconsistente para {metadata.code}: "
                f"listalivros={chapter_count}, biblia={actual_chapter_count}."
            )

        source_books.append(
            SourceBook(
                abbreviation=metadata.code,
                chapter_count=chapter_count,
                name=source_name,
                testament=metadata.testament,
                canon_order=metadata.canon_order,
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
        "Job": set(),
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
        "Jo": {"joao", "john"},
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
