"""Text normalization used for lookups and features (never for offsets)."""
from __future__ import annotations

import unicodedata

_APOSTROPHES = str.maketrans({
    "’": "'", "‘": "'", "ʼ": "'", "`": "'", "´": "'",
})

# Older / informal Malian orthography writes ɛ as è and ɔ as ò ("n bè taa").
_OLD_ORTHOGRAPHY = str.maketrans({"è": "ɛ", "ò": "ɔ"})


def normalize(text: str) -> str:
    """NFC, unify apostrophes, lowercase."""
    return unicodedata.normalize("NFC", text).translate(_APOSTROPHES).lower()


def fold_old_orthography(text: str) -> str:
    """Map old-orthography vowels to the official letters (è→ɛ, ò→ɔ)."""
    return text.translate(_OLD_ORTHOGRAPHY)
