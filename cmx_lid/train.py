"""Train the word classifier.

Sources (all combined as unique word types):
  * gold/silver CoNLL files       --conll PATH (repeatable; default: seed train)
  * word lists from ingest        --wordlist PATH (repeatable; TSV word/label/count/purity)
  * single-label lexicon entries  (always)

    python -m cmx_lid.train
    python -m cmx_lid.train --conll data/silver/kunkado-train.conll \\
        --wordlist data/silver/wordlist.tsv --backend fasttext
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from . import paths
from .classifier import CLASSIFIER_LABELS, CharNgramNB
from .data_io import read_conll
from .augment import variants
from .lexicon import Lexicon
from .normalize import normalize

FT_MODEL_PATH = paths.ROOT / "models" / "cmx-lid-ft.ftz"


def conll_pairs(path) -> set[tuple[str, str]]:
    return {(normalize(tok), label) for sent in read_conll(path) for tok, label in sent
            if label in CLASSIFIER_LABELS}


def wordlist_pairs(path, min_count: int = 1, min_purity: float = 0.0) -> set[tuple[str, str]]:
    out = set()
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t"):
            if (row["label"] in CLASSIFIER_LABELS and int(row["count"]) >= min_count
                    and float(row["purity"]) >= min_purity):
                out.add((normalize(row["word"]), row["label"]))
    return out


def resolve_conflicts(pairs: set[tuple[str, str]], lexicon: Lexicon,
                      keep_ambiguous: bool = False) -> list[tuple[str, str]]:
    """A word type seen with several labels across sources: the curated lexicon
    settles it if it can; otherwise it is dropped, or (keep_ambiguous) kept under
    every label so the classifier learns it is genuinely shared (fr/en "or")."""
    by_word: dict[str, set[str]] = {}
    for w, l in pairs:
        by_word.setdefault(w, set()).add(l)
    out = []
    for w, labels in by_word.items():
        if len(labels) == 1:
            out.append((w, next(iter(labels))))
        else:
            lex = lexicon.labels_of(w)
            if len(lex) == 1 and lex <= labels:
                out.append((w, next(iter(lex))))
            elif keep_ambiguous:
                out.extend((w, l) for l in labels)
    return sorted(out)


def augment_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Add informal spellings of Bambara words, unless the form is already a
    real word of another language (be/de stay whatever the data says)."""
    taken = {w for w, _ in pairs}
    extra = {(v, "bam") for w, l in pairs if l == "bam" for v in variants(w) if v not in taken}
    return sorted(set(pairs) | extra)


def training_pairs(train_path, lexicon: Lexicon, extra_conll=(), wordlists=(),
                   min_count: int = 1, min_purity: float = 0.0, augment: bool = True,
                   keep_ambiguous: bool = True) -> list[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for p in [train_path, *extra_conll]:
        if p:
            pairs |= conll_pairs(p)
    for p in wordlists:
        pairs |= wordlist_pairs(p, min_count, min_purity)
    pairs |= {(f, l) for f, l in lexicon.single_label_items() if l in CLASSIFIER_LABELS}
    out = resolve_conflicts(pairs, lexicon, keep_ambiguous)
    return augment_pairs(out) if augment else out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", default=paths.TRAIN_PATH, help="seed CoNLL ('' to skip)")
    ap.add_argument("--conll", action="append", default=[], help="extra CoNLL file (repeatable)")
    ap.add_argument("--wordlist", action="append", default=[], help="word list TSV (repeatable)")
    ap.add_argument("--min-count", type=int, default=3, help="word list: min occurrences")
    ap.add_argument("--min-purity", type=float, default=0.9, help="word list: min label share")
    ap.add_argument("--lexicon", default=paths.LEXICON_PATH)
    ap.add_argument("--no-augment", action="store_true", help="skip informal-spelling variants")
    ap.add_argument("--drop-ambiguous", action="store_true",
                    help="drop words seen with several labels instead of keeping all")
    ap.add_argument("--backend", choices=("nb", "fasttext"), default="nb")
    ap.add_argument("--out", default=None, help="model path (default per backend)")
    # defaults tuned on the BAYƐLƐMABAGA dev split (see MODEL_CARD.md)
    ap.add_argument("--n-max", type=int, default=5, help="nb: max char n-gram")
    ap.add_argument("--alpha", type=float, default=0.1, help="nb: smoothing")
    ap.add_argument("--prune", type=int, default=1, help="nb: drop n-grams seen fewer times")
    ap.add_argument("--dim", type=int, default=16, help="fasttext: vector size")
    ap.add_argument("--epoch", type=int, default=25, help="fasttext: epochs")
    args = ap.parse_args(argv)

    pairs = training_pairs(args.train, Lexicon.load(args.lexicon), args.conll, args.wordlist,
                           args.min_count, args.min_purity, not args.no_augment,
                           not args.drop_ambiguous)
    per_label = dict(Counter(l for _, l in pairs))
    if args.backend == "nb":
        out = Path(args.out or paths.TRAIN_MODEL_PATH)
        model = CharNgramNB(n_max=args.n_max, alpha=args.alpha,
                            min_gram_count=args.prune).fit(pairs)
        model.save(out)
        detail = f"{model.vocab_size} n-grams, {out.stat().st_size // 1024} KB"
    else:
        from .fasttext_backend import FastTextClassifier
        out = FastTextClassifier.train(pairs, args.out or FT_MODEL_PATH, dim=args.dim,
                                       epoch=args.epoch)
        detail = f"{out.stat().st_size // 1024} KB"
    print(f"[{args.backend}] trained on {len(pairs)} word types {per_label}; {detail} -> {out}")
    if args.backend != "nb":
        print(f"use it with:  python -m cmx_lid --model {out} \"...\"")


if __name__ == "__main__":
    main()
