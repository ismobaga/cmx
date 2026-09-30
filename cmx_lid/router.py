"""Deterministic rules that fire before (hard) or after (orthographic) the lexicon.

Order in the pipeline:
  1. route_hard           - univ tokens (incl. roman numerals, Arabic script), N'Ko script,
                            Bambara letters ɛ ɔ ɲ ŋ
  2. lexicon lookup       - can override (3), e.g. informal "ké" listed as bam
  3. route_orthographic   - French diacritics, clitic tables
  4. classifier
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .tokenize import CLITIC, UNIV, RawToken

BAM_LETTERS = frozenset("ɛɔɲŋ")
# Tone-marked vowels that French never uses (scholarly Bambara).
BAM_TONE_VOWELS = frozenset("áíóúǎěǐǒǔ")
# French-only diacritics. è and ò are NOT here: old Bambara orthography uses them.
FRA_MARKS = frozenset("éêëâîïôûùüÿçœæà")

FRA_CLITICS = frozenset({"l'", "d'", "j'", "c'", "qu'", "jusqu'", "lorsqu'",
                         "puisqu'", "presqu'", "quoiqu'"})
BAM_CLITICS = frozenset({"k'", "b'", "y'"})
# n' m' t' s' are shared: left to context.


@dataclass(frozen=True)
class Route:
    label: str
    confidence: float
    rule: str
    final: bool  # True -> label is forced, emission still informs neighbours


def _is_arabic(ch: str) -> bool:
    cp = ord(ch)
    return (0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or
            0x08A0 <= cp <= 0x08FF or 0xFB50 <= cp <= 0xFDFF or
            0xFE70 <= cp <= 0xFEFF)


def _is_nko(ch: str) -> bool:
    return 0x07C0 <= ord(ch) <= 0x07FF


# Chapter/verse numbering (IV, VII, XII). Single I is excluded: it is the
# Bambara 2sg pronoun and English "I".
_ROMAN = re.compile(r"^(?=[IVXLCDM]{2,}$|[VXLCDM]$)M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$")


def route_hard(tok: RawToken) -> Route | None:
    if tok.kind == UNIV or _ROMAN.match(tok.text):
        return Route("univ", 1.0, "univ", True)
    norm = tok.norm
    # N'Ko is a script for Manding languages: Bambara by usage.
    if any(_is_nko(c) for c in norm):
        return Route("bam", 0.999, "nko-script", True)
    # Arabic script is not expected (schema 2.0 has no `ara`); keep stray
    # pasted verses neutral instead of letting the classifier guess.
    if any(_is_arabic(c) for c in norm):
        return Route("univ", 1.0, "arabic-script", True)
    if any(c in BAM_LETTERS for c in norm):
        return Route("bam", 0.999, "bambara-letter", True)
    return None


def route_orthographic(tok: RawToken, french_final: bool = True) -> Route | None:
    norm = tok.norm
    if tok.kind == CLITIC:
        if norm in FRA_CLITICS:
            return Route("fra", 0.95, "fra-clitic", False)
        if norm in BAM_CLITICS:
            return Route("bam", 0.95, "bam-clitic", False)
        return None
    if any(c in FRA_MARKS for c in norm):
        return Route("fra", 0.97, "fra-orthography", french_final)
    if any(c in BAM_TONE_VOWELS for c in norm):
        return Route("bam", 0.9, "bam-tone", False)
    return None
