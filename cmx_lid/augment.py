"""Informal-spelling variants of Bambara words.

Bambara on phones is rarely written with ɛ ɔ ɲ ŋ. People strip them (bɛ -> be),
use French-style letters (bè, gn), or colonial-era spelling (dugu -> dougou,
cɛ -> tche). Words written with ɛ/ɔ are caught by the router and never reach the
classifier, so the classifier must learn the *informal* shapes instead.
"""
from __future__ import annotations

import random

STRIPPED = {"ɛ": "e", "ɔ": "o", "ɲ": "ny", "ŋ": "ng"}
OLD_FRENCH_STYLE = {"ɛ": "è", "ɔ": "ò", "ɲ": "gn", "ŋ": "ng"}
# applied after one of the maps above
COLONIAL = (("c", "tch"), ("j", "dj"), ("u", "ou"))


def _apply(word: str, table: dict[str, str]) -> str:
    return "".join(table.get(ch, ch) for ch in word)


def _colonial(word: str) -> str:
    for a, b in COLONIAL:
        word = word.replace(a, b)
    return word


def variants(word: str) -> set[str]:
    """All informal spellings of a (standard-orthography) Bambara word, excluding itself."""
    out = set()
    for table in (STRIPPED, OLD_FRENCH_STYLE):
        v = _apply(word, table)
        out.add(v)
        out.add(_colonial(v))
    out.discard(word)
    return out


def informalize(text: str, rng: random.Random, p_colonial: float = 0.25) -> str:
    """Rewrite a standard Bambara sentence the way it is often typed."""
    table = STRIPPED if rng.random() < 0.7 else OLD_FRENCH_STYLE
    words = []
    for w in text.split(" "):
        v = _apply(w, table)
        if rng.random() < p_colonial:
            v = _colonial(v)
        words.append(v)
    return " ".join(words)
