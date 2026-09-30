"""FROZEN output schema for cmx-lid.

Anything in this file is a public contract. Changing a label, a source, or a
Token field is a breaking change: bump SCHEMA_VERSION (major) and update the
fingerprint pinned in tests/test_schema.py and schema/token.schema.json.

Label semantics (usage, not etymology):
  bam  - Bambara, INCLUDING nativized loanwords of any origin
         (inchallah, al-hamdoulillah, lekɔli, taabali, lopital, opital).
  fra  - live French: French orthography (é, ô, ç, elision l'/d'/qu'...)
         or unassimilated French words.
  eng  - live English.
  univ - language-neutral: punctuation, numbers, emoji, URLs, @/#tags,
         roman numerals, and any Arabic-script text (not expected in input).

2.0.0: dropped `ara`. Latin-script Arabic loans were always `bam`; Arabic
script now goes to `univ`.

Loanword ORIGIN is deliberately not part of this schema. It lives in the
side table read by cmx_lid.origins and is never fed to the classifier.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields

SCHEMA_VERSION = "2.0.0"

LANG_LABELS: tuple[str, ...] = ("bam", "fra", "eng")
NON_LANG_LABELS: tuple[str, ...] = ("univ",)
LABELS: tuple[str, ...] = LANG_LABELS + NON_LANG_LABELS

# Which pipeline stage decided the label.
SOURCES: tuple[str, ...] = ("router", "lexicon", "classifier", "context")


@dataclass(frozen=True)
class Token:
    text: str          # exact substring of the input
    start: int         # char offset (inclusive) into the input
    end: int           # char offset (exclusive)
    label: str         # one of LABELS
    confidence: float  # posterior probability of `label`, 0..1
    source: str        # one of SOURCES

    def __post_init__(self) -> None:
        if self.label not in LABELS:
            raise ValueError(f"unknown label {self.label!r}")
        if self.source not in SOURCES:
            raise ValueError(f"unknown source {self.source!r}")

    def to_dict(self) -> dict:
        return asdict(self)


def fingerprint() -> str:
    """Stable hash of the contract; pinned by tests to catch silent drift."""
    payload = {
        "version": SCHEMA_VERSION,
        "labels": list(LABELS),
        "sources": list(SOURCES),
        "token_fields": [f.name for f in fields(Token)],
    }
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
