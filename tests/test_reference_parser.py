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


def test_extract_all_handles_chapter_only_and_common_punctuation() -> None:
    parser = ReferenceParser()

    references = parser.extract_all("Leia Sl 23, Jo 3,16 e 1 Cor 13:4-7 hoje.")

    assert len(references) == 3
    assert references[0].book_alias == "sl"
    assert references[0].chapter == 23
    assert references[0].verse_start is None
    assert references[1].book_alias == "jo"
    assert references[1].chapter == 3
    assert references[1].verse_start == 16
    assert references[2].book_alias == "1 cor"
    assert references[2].chapter == 13
    assert references[2].verse_start == 4
    assert references[2].verse_end == 7
