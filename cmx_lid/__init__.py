"""cmx-lid: word-level language identification for Bambara with French/English switches.

Quick use:

    >>> import cmx_lid
    >>> cmx_lid.tag("n taara l'hôpital kunun")
    [('n', 'bam'), ('taara', 'bam'), ("l'", 'fra'), ('hôpital', 'fra'), ('kunun', 'bam')]
    >>> cmx_lid.detect("n taara l'hôpital kunun")      # main language of the text
    'bam'
    >>> cmx_lid.is_code_switched("n taara l'hôpital kunun")
    True

More detail: identify() returns Token objects (offsets, confidence, source),
summarize()/segments() give message-level views. Labels: bam, fra, eng, univ
(univ = punctuation, numbers, emoji, links).

Loanword origin metadata is available separately via `cmx_lid.origins`
and is never used for classification.
"""
from .pipeline import Config, Identifier, identify
from .schema import LABELS, LANG_LABELS, SCHEMA_VERSION, Token
from .summary import Segment, Summary, segments, summarize


def tag(text: str, include_punct: bool = False) -> list[tuple[str, str]]:
    """[(word, label), ...]. Punctuation/numbers/emoji are left out unless include_punct."""
    return [(t.text, t.label) for t in identify(text) if include_punct or t.label != "univ"]


def detect(text: str) -> str | None:
    """Main language of the text: 'bam', 'fra', 'eng', or None if it has no words."""
    return summarize(identify(text)).dominant


def is_code_switched(text: str) -> bool:
    """True if the text mixes languages."""
    return summarize(identify(text)).code_switched


__all__ = ["tag", "detect", "is_code_switched", "identify", "summarize", "segments",
           "Identifier", "Config", "Token", "Summary", "Segment",
           "LABELS", "LANG_LABELS", "SCHEMA_VERSION"]
__version__ = "0.5.0"
