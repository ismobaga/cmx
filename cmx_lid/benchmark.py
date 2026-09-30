"""Benchmark suites built from BAYƐLƐMABAGA dev/test splits (never trained on).

  bam        real Bambara sentences, every word gold `bam`
             (silver: real French switches/names inside are also counted bam)
  fra        real French sentences, gold `fra`
  bam-inf    the Bambara sentences re-spelled informally (be, mogo, dougou, tche)
  cs-synth   Bambara sentence + 1-3 word French span from its aligned translation
             spliced in at a random word boundary (insertional code-switching)

    python -m cmx_lid.benchmark --split test [--model models/cmx-lid-ft.ftz]

Scores are word-level (punctuation/numbers excluded). cs-synth also reports
F1 on the inserted French words: the number that matters for switch detection.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from . import paths
from .augment import informalize
from .pipeline import Identifier
from .tokenize import WORD, tokenize

BAYELEMABAGA = paths.DATA_DIR / "raw" / "bayelemabaga"
SPLIT_FILES = {"dev": ("valid/dev.bam", "valid/dev.fr"),
               "test": ("test/test.bam", "test/test.fr")}


def load_pairs(split: str, limit: int | None = None) -> list[tuple[str, str]]:
    b, f = SPLIT_FILES[split]
    if not (BAYELEMABAGA / b).exists():
        raise FileNotFoundError(
            f"{BAYELEMABAGA / b} missing. Download the split files from "
            "https://github.com/RobotsMali-AI/datasets/tree/main/bayelemabaga "
            "(valid/dev.*, test/test.*) into data/raw/bayelemabaga/")
    bam = (BAYELEMABAGA / b).read_text(encoding="utf-8").splitlines()
    fra = (BAYELEMABAGA / f).read_text(encoding="utf-8").splitlines()
    pairs = [(x.strip(), y.strip()) for x, y in zip(bam, fra) if x.strip() and y.strip()]
    return pairs[:limit] if limit else pairs


def _score(ident: Identifier, items) -> dict:
    """items: iterable of (text, gold_fn(start)->label)."""
    n = correct = 0
    tp = fp = fn = 0
    for text, gold_at in items:
        for t in ident.identify(text):
            if t.label == "univ":
                continue
            g = gold_at(t.start)
            n += 1
            correct += t.label == g
            if t.label == "fra" and g == "fra":
                tp += 1
            elif t.label == "fra":
                fp += 1
            elif g == "fra":
                fn += 1
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"words": n, "acc": correct / n if n else 0.0, "fra_p": p, "fra_r": r,
            "fra_f1": 2 * p * r / (p + r) if p + r else 0.0}


def _splice(bam: str, fra: str, rng: random.Random):
    fwords = [t.text for t in tokenize(fra) if t.kind == WORD]
    bwords = bam.split(" ")
    if len(fwords) < 1 or len(bwords) < 2:
        return None
    k = rng.randint(1, min(3, len(fwords)))
    i = rng.randrange(0, len(fwords) - k + 1)
    picked = fwords[i:i + k]
    if i == 0:  # sentence-initial capital would not survive a mid-sentence switch
        picked[0] = picked[0][:1].lower() + picked[0][1:]
    span = " ".join(picked)
    cut = rng.randrange(1, len(bwords))
    left = " ".join(bwords[:cut])
    text = f"{left} {span} {' '.join(bwords[cut:])}"
    lo, hi = len(left) + 1, len(left) + 1 + len(span)
    return text, (lambda s, lo=lo, hi=hi: "fra" if lo <= s < hi else "bam")


def run(ident: Identifier, split: str = "dev", limit: int | None = None, seed: int = 13) -> dict:
    pairs = load_pairs(split, limit)
    rng = random.Random(seed)
    res = {
        "bam": _score(ident, ((b, lambda s: "bam") for b, _ in pairs)),
        "fra": _score(ident, ((f, lambda s: "fra") for _, f in pairs)),
        "bam-inf": _score(ident, ((informalize(b, rng), lambda s: "bam") for b, _ in pairs)),
    }
    rng = random.Random(seed)
    spliced = [x for x in (_splice(b, f, rng) for b, f in pairs) if x]
    res["cs-synth"] = _score(ident, spliced)
    res["macro_acc"] = sum(res[k]["acc"] for k in ("bam", "fra", "bam-inf", "cs-synth")) / 4
    return res


def print_table(res: dict, title: str = "") -> None:
    if title:
        print(title)
    print(f"  {'suite':9} {'words':>7} {'acc':>6} {'fraF1':>6}")
    for k in ("bam", "fra", "bam-inf", "cs-synth"):
        m = res[k]
        f1 = f"{m['fra_f1']:.3f}" if k in ("cs-synth", "fra") else "   -  "
        print(f"  {k:9} {m['words']:7d} {m['acc']:6.3f} {f1:>6}")
    print(f"  macro acc {res['macro_acc']:.3f}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=tuple(SPLIT_FILES), default="dev")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--json", help="also write results to this file")
    args = ap.parse_args(argv)
    ident = Identifier.load(model_path=args.model) if args.model else Identifier.load()
    res = run(ident, args.split, args.limit)
    print_table(res, f"[{args.split}] {args.model or paths.MODEL_PATH.name}")
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
