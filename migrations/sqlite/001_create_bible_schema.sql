CREATE TABLE IF NOT EXISTS translations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    language TEXT NOT NULL,
    canon TEXT NOT NULL,
    source TEXT,
    license TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    abbreviation TEXT NOT NULL,
    name TEXT NOT NULL,
    testament TEXT NOT NULL,
    canon_order INTEGER NOT NULL,
    chapter_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS book_aliases (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
    UNIQUE (book_id, normalized_alias)
);

CREATE INDEX IF NOT EXISTS idx_book_aliases_normalized_alias
    ON book_aliases (normalized_alias);

CREATE TABLE IF NOT EXISTS verses (
    id INTEGER PRIMARY KEY,
    translation_id TEXT NOT NULL,
    book_id INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY (translation_id) REFERENCES translations (id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
    UNIQUE (translation_id, book_id, chapter, verse)
);

CREATE INDEX IF NOT EXISTS idx_verses_lookup
    ON verses (translation_id, book_id, chapter, verse);
