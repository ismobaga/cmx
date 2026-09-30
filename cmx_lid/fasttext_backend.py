"""Optional fastText word classifier (pip install fasttext-wheel).

Same interface as the built-in Naive Bayes: predict_proba(word) -> {bam, fra, eng}.
Trained on OUR word-level labels (usage policy), not a pretrained LID model.
Pretrained sentence-level models (GlotLID, lid.176) label by etymology and are
unreliable on single words; use them only as message-level filters.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable

from .classifier import CLASSIFIER_LABELS
from .normalize import normalize

_PREFIX = "__label__"


def _fasttext():
    try:
        import fasttext  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError("fastText backend needs `pip install fasttext-wheel`") from e
    fasttext.FastText.eprint = lambda *a, **k: None  # silence load warning
    return fasttext


class FastTextClassifier:
    def __init__(self, model):
        self._m = model

    @classmethod
    def load(cls, path: str | Path) -> "FastTextClassifier":
        return cls(_fasttext().load_model(str(path)))

    @classmethod
    def train(cls, pairs: Iterable[tuple[str, str]], out_path: str | Path, *,
              dim: int = 32, epoch: int = 40, lr: float = 0.5, minn: int = 1,
              maxn: int = 5, quantize: bool = True) -> Path:
        ft = _fasttext()
        fd, tmp = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for word, label in pairs:
                    if label in CLASSIFIER_LABELS:
                        f.write(f"{_PREFIX}{label} {normalize(word)}\n")
            model = ft.train_supervised(input=tmp, dim=dim, epoch=epoch, lr=lr, minn=minn,
                                        maxn=maxn, wordNgrams=1, bucket=50_000,
                                        minCount=1, loss="softmax", verbose=0)
            out = Path(out_path)
            if quantize:
                try:
                    model.quantize(input=tmp, retrain=True, qnorm=True)
                    out = out.with_suffix(".ftz")
                except Exception as e:  # tiny datasets can fail to quantize
                    print(f"quantize skipped ({e}); saving full .bin")
                    out = out.with_suffix(".bin")
            else:
                out = out.with_suffix(".bin")
            out.parent.mkdir(parents=True, exist_ok=True)
            model.save_model(str(out))
            return out
        finally:
            os.unlink(tmp)

    def predict_proba(self, word: str) -> dict[str, float]:
        text = normalize(word).replace("\n", " ")
        # Call the C++ binding directly: fastText's Python predict() breaks on NumPy 2.
        raw = self._m.f.predict(text, -1, 0.0, "strict")
        got = {lab[len(_PREFIX):]: float(p) for p, lab in raw}
        probs = {l: max(got.get(l, 0.0), 1e-6) for l in CLASSIFIER_LABELS}
        z = sum(probs.values())
        return {l: p / z for l, p in probs.items()}
