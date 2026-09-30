"""Message-level views over labeled tokens (not part of the frozen Token schema).

    >>> s = summarize(identify("n taara l'hôpital kunun"))
    >>> s.dominant, s.code_switched, [x.label for x in segments(...)]
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .schema import LANG_LABELS, Token


@dataclass(frozen=True)
class Segment:
    label: str
    start: int   # char offset of first token
    end: int     # char offset after last token
    n_words: int


@dataclass(frozen=True)
class Summary:
    dominant: str | None          # most frequent language (None if no words)
    proportions: dict[str, float] # share of words per language
    code_switched: bool           # more than one language present
    n_words: int
    n_switches: int               # language changes between consecutive words


def segments(tokens: Sequence[Token]) -> list[Segment]:
    """Runs of same-language words. Punctuation/numbers never split a run."""
    out: list[Segment] = []
    for t in tokens:
        if t.label not in LANG_LABELS:
            continue
        if out and out[-1].label == t.label:
            last = out[-1]
            out[-1] = Segment(last.label, last.start, t.end, last.n_words + 1)
        else:
            out.append(Segment(t.label, t.start, t.end, 1))
    return out


def summarize(tokens: Sequence[Token]) -> Summary:
    words = [t.label for t in tokens if t.label in LANG_LABELS]
    counts = Counter(words)
    n = len(words)
    props = {l: counts[l] / n for l in LANG_LABELS if counts[l]} if n else {}
    dominant = max(props, key=lambda l: (props[l], l == "bam")) if props else None
    switches = sum(1 for a, b in zip(words, words[1:]) if a != b)
    return Summary(dominant, props, len(props) > 1, n, switches)
