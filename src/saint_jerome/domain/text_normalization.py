from __future__ import annotations

import re
import unicodedata


def normalize_lookup_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    lowered = without_accents.casefold()
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(collapsed.split())
