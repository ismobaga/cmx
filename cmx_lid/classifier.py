"""Character n-gram multinomial Naive Bayes over word types.

Tiny, dependency-free, JSON-serializable: suitable for on-device use.
Only sees (word, label) pairs. It never sees loanword origin.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable, Protocol

from .normalize import normalize

CLASSIFIER_LABELS: tuple[str, ...] = ("bam", "fra", "eng")
FORMAT = "cmx-lid/char-ngram-nb/1"


class WordClassifier(Protocol):
    """What the pipeline needs from any backend."""

    def predict_proba(self, word: str) -> dict[str, float]: ...


def load_classifier(path: str | Path) -> WordClassifier:
    """.json -> built-in Naive Bayes; .ftz / .bin -> fastText (optional dependency)."""
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return CharNgramNB.load(path)
    if suffix in (".ftz", ".bin"):
        from .fasttext_backend import FastTextClassifier
        return FastTextClassifier.load(path)
    raise ValueError(f"don't know how to load classifier {path!r}")


class CharNgramNB:
    def __init__(self, labels: Iterable[str] = CLASSIFIER_LABELS,
                 n_min: int = 1, n_max: int = 5, alpha: float = 0.1, temp_power: float = 0.5,
                 min_gram_count: int = 1):
        self.labels = tuple(labels)
        self.n_min, self.n_max, self.alpha = n_min, n_max, alpha
        self.temp_power = temp_power  # likelihood divided by (#grams ** temp_power)
        self.min_gram_count = min_gram_count  # prune rarer n-grams (smaller on-device model)
        self.counts: dict[str, dict[str, int]] = {l: {} for l in self.labels}
        self.totals: dict[str, int] = {l: 0 for l in self.labels}
        self.log_priors: dict[str, float] = {l: -math.log(len(self.labels)) for l in self.labels}
        self.vocab_size = 0

    def grams(self, word: str) -> list[str]:
        w = f"<{normalize(word)}>"
        out = []
        for n in range(self.n_min, self.n_max + 1):
            for i in range(len(w) - n + 1):
                g = w[i:i + n]
                if g not in ("<", ">"):
                    out.append(g)
        return out

    def fit(self, pairs: Iterable[tuple[str, str]]) -> "CharNgramNB":
        counts = {l: Counter() for l in self.labels}
        docs = Counter()
        for word, label in pairs:
            if label not in counts:
                continue
            docs[label] += 1
            counts[label].update(self.grams(word))
        if self.min_gram_count > 1:
            total = Counter()
            for c in counts.values():
                total.update(c)
            keep = {g for g, n in total.items() if n >= self.min_gram_count}
            counts = {l: Counter({g: n for g, n in c.items() if g in keep}) for l, c in counts.items()}
        n_docs = sum(docs.values())
        if n_docs == 0:
            raise ValueError("no training pairs")
        k = len(self.labels)
        self.counts = {l: dict(c) for l, c in counts.items()}
        self.totals = {l: sum(c.values()) for l, c in counts.items()}
        self.log_priors = {l: math.log((docs[l] + 1) / (n_docs + k)) for l in self.labels}
        self.vocab_size = len(set().union(*counts.values()))
        return self

    def predict_proba(self, word: str) -> dict[str, float]:
        grams = self.grams(word)
        if not grams:
            return {l: 1 / len(self.labels) for l in self.labels}
        denom_v = self.alpha * (self.vocab_size + 1)
        # Divide the likelihood by #grams**temp_power so long words aren't absurdly
        # overconfident; keeps emissions usable by the context decoder.
        temp = len(grams) ** self.temp_power
        scores = {}
        for l in self.labels:
            c, tot = self.counts[l], self.totals[l]
            ll = sum(math.log((c.get(g, 0) + self.alpha) / (tot + denom_v)) for g in grams)
            scores[l] = self.log_priors[l] + ll / temp
        m = max(scores.values())
        exp = {l: math.exp(s - m) for l, s in scores.items()}
        z = sum(exp.values())
        return {l: v / z for l, v in exp.items()}

    def to_dict(self) -> dict:
        return {"format": FORMAT, "labels": list(self.labels), "n_min": self.n_min,
                "n_max": self.n_max, "alpha": self.alpha, "temp_power": self.temp_power, "log_priors": self.log_priors,
                "totals": self.totals, "vocab_size": self.vocab_size, "counts": self.counts}

    @classmethod
    def from_dict(cls, d: dict) -> "CharNgramNB":
        if d.get("format") != FORMAT:
            raise ValueError(f"unsupported model format {d.get('format')!r}")
        m = cls(d["labels"], d["n_min"], d["n_max"], d["alpha"], d.get("temp_power", 0.5))
        m.log_priors, m.totals = d["log_priors"], d["totals"]
        m.vocab_size, m.counts = d["vocab_size"], d["counts"]
        return m

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CharNgramNB":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
