"""Parallel or monolingual text -> labeled word list for the classifier.

Counts every word on each language side and keeps words whose label share
("purity") is high. Names, numbers and shared function words (a, la, ni)
appear on both sides, get low purity, and are filtered out at training time.
French switches inside Bambara sentences are outnumbered by the French side.

  # source/target pairs with language columns (djelia/bambara-mt-dataset:
  # source_text/target_text + source_lang/target_lang = bam_Latn/fra_Latn/eng_Latn)
  python -m cmx_lid.ingest.wordlist --hf djelia/bambara-mt-dataset --split all \\
      --out data/silver/wl-djelia.tsv
  # one column per language instead (e.g. bm / fr / en)
  python -m cmx_lid.ingest.wordlist --jsonl rows.jsonl --col bam=bm --col fra=fr --col eng=en ...
  python -m cmx_lid.ingest.wordlist --hf oza75/bambara-mt --config <config> \\
      --limit 200000 --out data/silver/wordlist.tsv
  # drop subsets whose license you can't use (e.g. non-commercial sources)
  ... --drop-source bamadaba --drop-source corbama
  # monolingual text files (one sentence per line)
  python -m cmx_lid.ingest.wordlist --text bam=data/raw/bm_wiki.txt \\
      --text fra=data/raw/fr.txt --out data/silver/wordlist.tsv
  # frequency lists ("word count" per line)
  python -m cmx_lid.ingest.wordlist --freq eng=en_50k.txt --limit 10000 --out data/silver/wl-en.tsv

Output TSV: word, label, count, purity (all labels' counts in `counts`).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from ..router import route_hard
from ..tokenize import WORD, tokenize
from .hf import iter_hf_parquet, iter_hf_rows, iter_jsonl, list_splits, pyarrow_available

LANG_ALIASES = {
    "bam": "bam", "bm": "bam", "bambara": "bam", "bam_latn": "bam", "bamanankan": "bam",
    "fra": "fra", "fr": "fra", "french": "fra", "fra_latn": "fra", "fre": "fra",
    "eng": "eng", "en": "eng", "english": "eng", "eng_latn": "eng",
}


def canon(code) -> str | None:
    return LANG_ALIASES.get(str(code or "").strip().lower())


class Counts:
    def __init__(self):
        self.by_word: dict[str, Counter] = defaultdict(Counter)

    def add(self, text: str, lang: str) -> None:
        for tok in tokenize(text or ""):
            if tok.kind != WORD:
                continue
            hard = route_hard(tok)
            if hard and hard.label != lang:
                continue  # e.g. a word with ɛ on the French side: noise, skip
            self.by_word[tok.norm][lang] += 1

    def add_count(self, word: str, lang: str, n: int) -> None:
        toks = tokenize(word)
        if len(toks) == 1 and toks[0].kind == WORD:
            hard = route_hard(toks[0])
            if not hard or hard.label == lang:
                self.by_word[toks[0].norm][lang] += n

    def rows(self) -> Iterable[tuple[str, str, int, float, str]]:
        for word, c in sorted(self.by_word.items()):
            total = sum(c.values())
            label, n = c.most_common(1)[0]
            detail = ",".join(f"{l}:{v}" for l, v in sorted(c.items()))
            yield word, label, total, n / total, detail


def _check_layout(row: dict, col_map: list, args) -> list:
    """Look at the first row and fail loudly instead of silently counting nothing."""
    keys = sorted(row)
    if col_map:
        if any(c in row for _, c in col_map):
            return col_map
        if args.src_col in row and args.tgt_col in row:
            print(f"note: columns {[c for _, c in col_map]} not found; rows are "
                  f"{args.src_col}/{args.tgt_col} pairs with language columns, using those "
                  f"(drop --col for this dataset)")
            return []
        raise SystemExit(f"none of the --col columns {[c for _, c in col_map]} exist; "
                         f"row columns are {keys}")
    if args.src_col not in row or args.tgt_col not in row:
        raise SystemExit(f"rows have no {args.src_col!r}/{args.tgt_col!r} columns; row columns "
                         f"are {keys}. Use --col LANG=COLUMN or --src-col/--tgt-col.")
    return col_map


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_argument_group("parallel source (HF API or JSONL)")
    src.add_argument("--hf", help="dataset id, e.g. oza75/bambara-mt")
    src.add_argument("--config", default="default")
    src.add_argument("--split", default="train", help="split name, or 'all'")
    src.add_argument("--via", choices=("auto", "parquet", "rows"), default="auto",
                     help="parquet: one download per split (needs pyarrow, avoids 429s); "
                          "rows: page through the API; auto: parquet if pyarrow is installed")
    src.add_argument("--col", action="append", default=[], metavar="LANG=COLUMN",
                     help="one text column per language, e.g. --col bam=bm --col fra=fr "
                          "(replaces the source/target options)")
    src.add_argument("--jsonl", help="local JSONL export with the same columns")
    src.add_argument("--src-col", default="source_text")
    src.add_argument("--tgt-col", default="target_text")
    src.add_argument("--src-lang-col", default="source_lang")
    src.add_argument("--tgt-lang-col", default="target_lang")
    src.add_argument("--src-lang", help="fixed source language if there is no lang column")
    src.add_argument("--tgt-lang", help="fixed target language if there is no lang column")
    src.add_argument("--source-col", default="dataset_source", help="provenance column")
    src.add_argument("--drop-source", action="append", default=[],
                     help="skip rows whose provenance contains this substring (repeatable)")
    ap.add_argument("--text", action="append", default=[], metavar="LANG=PATH",
                    help="monolingual file, one sentence per line (repeatable)")
    ap.add_argument("--freq", action="append", default=[], metavar="LANG=PATH",
                    help="frequency list, 'word count' per line (e.g. FrequencyWords) (repeatable)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    counts, stats = Counts(), Counter()
    if args.hf or args.jsonl:
        col_map = []
        for spec in args.col:
            lang_code, _, column = spec.partition("=")
            if not canon(lang_code) or not column:
                ap.error(f"--col expects LANG=COLUMN, got {spec!r}")
            col_map.append((canon(lang_code), column))
        via = args.via
        if via == "auto":
            via = "parquet" if pyarrow_available() else "rows"
            if via == "rows":
                print("tip: `pip install pyarrow` downloads whole splits and avoids 429 errors")
        if args.jsonl:
            rows = iter_jsonl(args.jsonl, args.limit)
        elif via == "parquet":
            cfg = None if args.config == "default" else args.config
            rows = iter_hf_parquet(args.hf, cfg, args.split, None, args.limit)
        elif args.split == "all":
            targets = list_splits(args.hf)
            print(f"splits: {targets}")
            rows = (r for cfg, sp in targets
                    for r in iter_hf_rows(args.hf, cfg, sp, None, args.limit))
        else:
            rows = iter_hf_rows(args.hf, args.config, args.split, None, args.limit)
        checked = False
        for row in rows:
            stats["rows"] += 1
            if not checked:
                col_map = _check_layout(row, col_map, args)
                checked = True
            if col_map:
                for lang, column in col_map:
                    if row.get(column):
                        counts.add(row[column], lang)
                        stats[f"side_{lang}"] += 1
                continue
            prov = str(row.get(args.source_col) or "").lower()
            if any(d.lower() in prov for d in args.drop_source):
                stats["dropped_by_source"] += 1
                continue
            for text_col, lang_col, fixed in ((args.src_col, args.src_lang_col, args.src_lang),
                                              (args.tgt_col, args.tgt_lang_col, args.tgt_lang)):
                lang = canon(fixed or row.get(lang_col))
                if lang:
                    counts.add(row.get(text_col), lang)
                    stats[f"side_{lang}"] += 1
                else:
                    stats["unknown_lang"] += 1
    for spec in args.text:
        lang_code, _, path = spec.partition("=")
        lang = canon(lang_code)
        if not lang or not path:
            ap.error(f"--text expects LANG=PATH, got {spec!r}")
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if args.limit and i >= args.limit:
                    break
                counts.add(line, lang)
                stats[f"lines_{lang}"] += 1

    for spec in args.freq:
        lang_code, _, path = spec.partition("=")
        lang = canon(lang_code)
        if not lang or not path:
            ap.error(f"--freq expects LANG=PATH, got {spec!r}")
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if args.limit and i >= args.limit:
                    break
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit():
                    counts.add_count(parts[0], lang, int(parts[1]))
                    stats[f"freq_{lang}"] += 1

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    kept = Counter()
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# generated by cmx_lid.ingest.wordlist; check source licenses (DATA.md)\n")
        f.write("word\tlabel\tcount\tpurity\tcounts\n")
        for word, label, total, purity, detail in counts.rows():
            f.write(f"{word}\t{label}\t{total}\t{purity:.3f}\t{detail}\n")
            kept[label] += 1
    print(f"{args.out}: {dict(stats)} -> word types {dict(kept)}")


if __name__ == "__main__":
    main()
