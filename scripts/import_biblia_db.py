from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from saint_jerome.infra.importers.biblia_db import (
    BOOK_METADATA,
    DEFAULT_BIBLIA_JSON_URL,
    DEFAULT_LICENSE,
    DEFAULT_LISTA_LIVROS_URL,
    DEFAULT_TRANSLATION_ID,
    DEFAULT_TRANSLATION_NAME,
    SourceBook,
    _build_source_books,
    apply_sqlite_migration,
    cli_main as main,
    import_translation,
)

__all__ = [
    "BOOK_METADATA",
    "DEFAULT_BIBLIA_JSON_URL",
    "DEFAULT_LICENSE",
    "DEFAULT_LISTA_LIVROS_URL",
    "DEFAULT_TRANSLATION_ID",
    "DEFAULT_TRANSLATION_NAME",
    "SourceBook",
    "_build_source_books",
    "apply_sqlite_migration",
    "import_translation",
    "main",
]


if __name__ == "__main__":
    main()
