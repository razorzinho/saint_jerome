from __future__ import annotations

import asyncio
import logging

from saint_jerome.config.settings import Settings
from saint_jerome.infra.importers.biblia_db import (
    DEFAULT_LICENSE,
    DEFAULT_TRANSLATION_ID,
    DEFAULT_TRANSLATION_NAME,
    ensure_postgres_schema,
    ensure_sqlite_schema,
    has_translation_postgres,
    has_translation_sqlite,
    import_translation_postgres,
    import_translation_sqlite,
    load_source_books,
)

logger = logging.getLogger("saint_jerome.bootstrap")


def bootstrap_database(settings: Settings) -> None:
    if settings.uses_postgres:
        asyncio.run(_bootstrap_postgres(settings))
        return

    _bootstrap_sqlite(settings)


def _bootstrap_sqlite(settings: Settings) -> None:
    if settings.auto_migrate_on_startup:
        ensure_sqlite_schema(
            db_path=settings.database_file,
            project_root=settings.base_dir,
        )
        logger.info("SQLite schema ensured on startup.")

    if not settings.auto_import_biblia_db_on_startup:
        return

    if has_translation_sqlite(
        db_path=settings.database_file,
        translation_id=DEFAULT_TRANSLATION_ID,
    ):
        logger.info(
            "SQLite already has translation %s. Skipping startup import.",
            DEFAULT_TRANSLATION_ID,
        )
        return

    logger.info("Importing biblia-db into SQLite on startup.")
    source_books = load_source_books(
        source_file=settings.biblia_db_source_file,
        books_file=settings.biblia_db_books_file,
        source_url=settings.biblia_db_source_url,
        books_url=settings.biblia_db_books_url,
    )
    import_translation_sqlite(
        db_path=settings.database_file,
        project_root=settings.base_dir,
        source_books=source_books,
        translation_id=DEFAULT_TRANSLATION_ID,
        translation_name=DEFAULT_TRANSLATION_NAME,
        language="pt-BR",
        canon="catholic",
        source_label=settings.biblia_db_source_url,
        license_label=DEFAULT_LICENSE,
        purge_translation=False,
    )


async def _bootstrap_postgres(settings: Settings) -> None:
    if settings.auto_migrate_on_startup:
        await ensure_postgres_schema(
            database_url=settings.database_url,
            project_root=settings.base_dir,
        )
        logger.info("Postgres schema ensured on startup.")

    if not settings.auto_import_biblia_db_on_startup:
        return

    if await has_translation_postgres(
        database_url=settings.database_url,
        translation_id=DEFAULT_TRANSLATION_ID,
    ):
        logger.info(
            "Postgres already has translation %s. Skipping startup import.",
            DEFAULT_TRANSLATION_ID,
        )
        return

    logger.info("Importing biblia-db into Postgres on startup.")
    source_books = await asyncio.to_thread(
        load_source_books,
        source_file=settings.biblia_db_source_file,
        books_file=settings.biblia_db_books_file,
        source_url=settings.biblia_db_source_url,
        books_url=settings.biblia_db_books_url,
    )
    await import_translation_postgres(
        database_url=settings.database_url,
        project_root=settings.base_dir,
        source_books=source_books,
        translation_id=DEFAULT_TRANSLATION_ID,
        translation_name=DEFAULT_TRANSLATION_NAME,
        language="pt-BR",
        canon="catholic",
        source_label=settings.biblia_db_source_url,
        license_label=DEFAULT_LICENSE,
        purge_translation=False,
    )
