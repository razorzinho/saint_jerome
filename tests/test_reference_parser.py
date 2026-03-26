from saint_jerome.domain.parser import ReferenceParser


def test_parser_handles_single_verse() -> None:
    parser = ReferenceParser()

    reference = parser.parse("Joao 3:16")

    assert reference.book_alias == "joao"
    assert reference.chapter == 3
    assert reference.verse_start == 16
    assert reference.verse_end is None


def test_parser_handles_chapter_only() -> None:
    parser = ReferenceParser()

    reference = parser.parse("Salmo 23")

    assert reference.book_alias == "salmo"
    assert reference.chapter == 23
    assert reference.verse_start is None
