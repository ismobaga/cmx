"""Usage-based lexicon: form -> label weights.

File format (data/lexicon.tsv), `#` comments allowed:
    taara	bam
    la	bam:0.6,fra:0.4      # ambiguous; weights are a prior, context decides

Nativized loanwords are listed with the label of the language they are USED
in (inchallah -> bam). Their origin is NOT recorded here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Mapping

from .normalize import fold_old_orthography, normalize
from .schema import LANG_LABELS


class Lexicon:
    def __init__(self, entries: Mapping[str, Mapping[str, float]]):
        self._entries: dict[str, dict[str, float]] = {}
        for form, weights in entries.items():
            bad = set(weights) - set(LANG_LABELS)
            if bad:
                raise ValueError(f"{form!r}: labels {sorted(bad)} not in {LANG_LABELS}")
            total = sum(weights.values())
            if total <= 0:
                raise ValueError(f"{form!r}: weights must be positive")
            self._entries[normalize(form)] = {k: v / total for k, v in weights.items()}

    @classmethod
    def load(cls, path: str | Path) -> "Lexicon":
        entries: dict[str, dict[str, float]] = {}
        for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                raise ValueError(f"{path}:{lineno}: expected 'form<TAB>labels'")
            form, spec = normalize(parts[0].strip()), parts[1].strip()
            if form in entries:
                raise ValueError(f"{path}:{lineno}: duplicate form {form!r}")
            weights: dict[str, float] = {}
            for item in spec.split(","):
                label, _, w = item.strip().partition(":")
                weights[label] = float(w) if w else 1.0
            entries[form] = weights
        return cls(entries)

    def lookup(self, form: str) -> dict[str, float] | None:
        norm = normalize(form)
        hit = self._entries.get(norm)
        if hit is None:
            folded = fold_old_orthography(norm)
            if folded != norm:
                hit = self._entries.get(folded)
        return dict(hit) if hit is not None else None

    def labels_of(self, form: str) -> frozenset[str]:
        hit = self.lookup(form)
        return frozenset(hit) if hit else frozenset()

    def single_label_items(self) -> Iterator[tuple[str, str]]:
        for form, weights in self._entries.items():
            if len(weights) == 1:
                yield form, next(iter(weights))

    def __contains__(self, form: str) -> bool:
        return self.lookup(form) is not None

    def __len__(self) -> int:
        return len(self._entries)
