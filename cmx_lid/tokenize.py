"""Offset-preserving tokenizer with clitic splitting.

Elided clitics are split from their host so each half is labeled on its own:
  l'hôpital -> l' + hôpital      (French elision)
  k'a       -> k' + a            (Bambara contraction of ka a)
English contractions (it's, we're, I'm) are left whole.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import normalize

WORD = "WORD"
CLITIC = "CLITIC"
UNIV = "UNIV"

_L = r"[^\W\d_]"             # any letter
_M = "[\u0300-\u036f\u07eb-\u07f5\u07fd]"  # combining marks: tones on ɛ/ɔ, N'Ko tones
_LM = rf"(?:{_L}|{_M})"
_APOS = "'’ʼ"

_TOKEN_RE = re.compile(
    rf"""
     (?P<url>(?:https?://|www\.)\S+)
    |(?P<email>[\w.+-]+@[\w-]+\.[\w.-]+)
    |(?P<tag>[@#]\w+)
    |(?P<num>\d+(?:[.,:/]\d+)*(?:{_LM}+\d*)*)
    |(?P<word>{_L}{_LM}*(?:[{_APOS}\-]{_L}{_LM}*)*)
    |(?P<other>\S)
    """,
    re.VERBOSE,
)

_CLITIC_RE = re.compile(
    rf"^((?:jusqu|lorsqu|puisqu|presqu|quoiqu|qu|{_L}{{1,2}})[{_APOS}])({_L}.*)$",
    re.IGNORECASE,
)
_EN_CONTRACTION_SUFFIXES = frozenset({"s", "t", "re", "ve", "ll", "d", "m"})

_WORD_FULL = re.compile(rf"^{_L}{_LM}*(?:[{_APOS}\-]{_L}{_LM}*)*$")
_CLITIC_FULL = re.compile(rf"^{_L}{{1,6}}[{_APOS}]$")


@dataclass(frozen=True)
class RawToken:
    text: str
    start: int
    end: int
    kind: str  # WORD | CLITIC | UNIV

    @property
    def norm(self) -> str:
        return normalize(self.text)


def _split_word(text: str, start: int) -> list[RawToken]:
    m = _CLITIC_RE.match(text)
    if m and normalize(m.group(2)) not in _EN_CONTRACTION_SUFFIXES:
        head, rest = m.group(1), m.group(2)
        cut = start + len(head)
        return [RawToken(head, start, cut, CLITIC),
                RawToken(rest, cut, cut + len(rest), WORD)]
    return [RawToken(text, start, start + len(text), WORD)]


def tokenize(text: str) -> list[RawToken]:
    out: list[RawToken] = []
    for m in _TOKEN_RE.finditer(text):
        if m.lastgroup == "word":
            out.extend(_split_word(m.group(), m.start()))
        else:
            out.append(RawToken(m.group(), m.start(), m.end(), UNIV))
    return out


def kind_of(word: str) -> str:
    """Kind of an already-tokenized word (used for gold / pre-tokenized input)."""
    if _CLITIC_FULL.match(word):
        return CLITIC
    if _WORD_FULL.match(word):
        return WORD
    return UNIV
