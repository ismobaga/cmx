"""Loanword ORIGIN side table: metadata only.

    Tag loanwords by usage (bam) for the model; record where they came from here.

Rules, enforced by tests/test_origins.py:
  * Only this module reads data/loanword_origin.tsv. The router, lexicon,
    classifier, pipeline and training code never import it.
  * The table has no label column. Every form in it must be labeled `bam`
    in the lexicon (nativized = Bambara by usage).
  * Use it post-hoc: annotate() takes tokens the model ALREADY labeled.

File format (TSV with header):
    form  origin_lang  source_form  gloss  notes
origin_lang is an ISO 639-3 code (ara, fra, eng, por, ...).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .normalize import fold_old_orthography, normalize
from .paths import resource
from .schema import Token

ORIGIN_TABLE_PATH = resource("loanword_origin.tsv")
COLUMNS = ("form", "origin_lang", "source_form", "gloss", "notes")
_ISO3 = re.compile(r"^[a-z]{3}$")


@dataclass(frozen=True)
class Origin:
    form: str
    origin_lang: str
    source_form: str
    gloss: str
    notes: str


class OriginTable:
    def __init__(self, rows: Iterable[Origin]):
        self._by_form: dict[str, Origin] = {}
        for r in rows:
            key = normalize(r.form)
            if key in self._by_form:
                raise ValueError(f"duplicate origin form {r.form!r}")
            if not _ISO3.match(r.origin_lang):
                raise ValueError(f"{r.form!r}: origin_lang must be ISO 639-3, got {r.origin_lang!r}")
            self._by_form[key] = r

    @classmethod
    def load(cls, path: str | Path = ORIGIN_TABLE_PATH) -> "OriginTable":
        lines = [l for l in Path(path).read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
        reader = csv.DictReader(lines, delimiter="\t")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{path}: header must be {COLUMNS}, got {reader.fieldnames}")
        return cls(Origin(**{k: (row[k] or "").strip() for k in COLUMNS}) for row in reader)

    def get(self, form: str) -> Origin | None:
        norm = normalize(form)
        return self._by_form.get(norm) or self._by_form.get(fold_old_orthography(norm))

    def forms(self) -> list[str]:
        return list(self._by_form)

    def by_origin(self, origin_lang: str) -> list[Origin]:
        return [o for o in self._by_form.values() if o.origin_lang == origin_lang]

    def annotate(self, tokens: Iterable[Token]) -> list[tuple[Token, Origin | None]]:
        """Attach origin to tokens the model labeled `bam`. Labels are untouched."""
        return [(t, self.get(t.text) if t.label == "bam" else None) for t in tokens]

    def __len__(self) -> int:
        return len(self._by_form)
