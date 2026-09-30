"""Evaluate on gold CoNLL data.

    python -m cmx_lid.evaluate [--dev PATH] [--errors]
"""
from __future__ import annotations

import argparse
from collections import Counter

from . import paths
from .data_io import read_conll
from .pipeline import Identifier
from .schema import LABELS


def evaluate(identifier: Identifier, gold) -> dict:
    conf = Counter()
    errors = []
    for sent in gold:
        words = [w for w, _ in sent]
        pred = identifier.identify_pretokenized(words)
        for (w, g), p in zip(sent, pred):
            conf[(g, p.label)] += 1
            if g != p.label:
                errors.append((" ".join(words), w, g, p.label, p.source))
    total = sum(conf.values())
    correct = sum(v for (g, p), v in conf.items() if g == p)
    per_label = {}
    for l in LABELS:
        tp = conf[(l, l)]
        fp = sum(v for (g, p), v in conf.items() if p == l and g != l)
        fn = sum(v for (g, p), v in conf.items() if g == l and p != l)
        if tp + fp + fn == 0:
            continue
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_label[l] = {"p": prec, "r": rec, "f1": f1, "support": tp + fn}
    return {"accuracy": correct / total if total else 0.0, "tokens": total,
            "per_label": per_label, "errors": errors}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dev", default=paths.DEV_PATH)
    ap.add_argument("--model", default=None, help="classifier file (.json NB or .ftz/.bin fastText)")
    ap.add_argument("--errors", action="store_true", help="print every mislabeled token")
    args = ap.parse_args(argv)

    res = evaluate((Identifier.load(model_path=args.model) if args.model else Identifier.load()), read_conll(args.dev))
    print(f"tokens {res['tokens']}  accuracy {res['accuracy']:.3f}")
    print(f"{'label':6} {'P':>6} {'R':>6} {'F1':>6} {'n':>5}")
    for l, m in res["per_label"].items():
        print(f"{l:6} {m['p']:6.3f} {m['r']:6.3f} {m['f1']:6.3f} {m['support']:5d}")
    if args.errors:
        for sent, w, g, p, src in res["errors"]:
            print(f"  {w!r}: gold={g} pred={p} ({src})  | {sent}")


if __name__ == "__main__":
    main()
