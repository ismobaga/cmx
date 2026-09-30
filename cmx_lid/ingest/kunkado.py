"""RobotsMali/kunkado -> token-labeled CoNLL (silver data for code-switching).

Kunkado (CC-BY-SA-4.0) is ~160 h of Malian radio transcribed in Bambara.
Annotators wrote French switches in French orthography between double
underscores, e.g.  "__Voila donc bon__ a man nɔgɔ __quoi__ a man nɔgɔn".
That matches our policy exactly: inside __..__ = fra, outside = bam (nativized
loans are written in Bambara orthography, so they land outside the markers).

    python -m cmx_lid.ingest.kunkado --split train --out data/silver/kunkado-train.conll
    python -m cmx_lid.ingest.kunkado --split test  --out data/silver/kunkado-test.conll
    python -m cmx_lid.ingest.kunkado --jsonl export.jsonl --out ...     # offline

The converted file is CC-BY-SA-4.0 like the source; keep the header.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from ..router import route_hard
from ..tokenize import UNIV, tokenize
from .hf import iter_hf_rows, iter_jsonl

DATASET = "RobotsMali/kunkado"
TEXT_COLUMNS = ("corrected-label", "semi-label")
# Annotation tags for noise/laughter/overlap etc. Check the dataset card and
# extend if its tag syntax differs.
TAG_RE = re.compile(r"\[[^\]]*\]|<[^>]*>|\{[^}]*\}|\([^)]*\)")


def convert(text: str) -> list[tuple[str, str]] | None:
    """Return [(token, label)] or None if the line is unusable."""
    text = TAG_RE.sub(" ", text or "")
    if not text.strip() or text.count("__") % 2:
        return None  # empty or unbalanced markers
    out: list[tuple[str, str]] = []
    for i, part in enumerate(text.split("__")):
        span_lang = "fra" if i % 2 else "bam"
        for tok in tokenize(part):
            if tok.kind == UNIV:
                out.append((tok.text, "univ"))
                continue
            hard = route_hard(tok)
            if hard and hard.label != span_lang:
                if span_lang == "fra" and hard.label == "bam":
                    return None  # Bambara letter inside a French span: annotation noise
                out.append((tok.text, hard.label))
            else:
                out.append((tok.text, span_lang))
    return out or None


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="human-reviewed", help="human-reviewed | semi-first | semi-second")
    ap.add_argument("--split", default="train")
    ap.add_argument("--jsonl", help="read rows from a local JSONL export instead of the API")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-switched", action="store_true",
                    help="keep only sentences that contain a French switch")
    args = ap.parse_args(argv)

    rows = (iter_jsonl(args.jsonl, args.limit) if args.jsonl else
            iter_hf_rows(DATASET, args.config, args.split, TEXT_COLUMNS, args.limit))
    stats = Counter()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# source: {DATASET} config={args.config} split={args.split}\n"
                "# license: CC-BY-SA-4.0 (derived data, share alike)\n"
                "# silver labels: __..__ spans -> fra, rest -> bam\n")
        for row in rows:
            stats["rows"] += 1
            text = row.get("corrected-label") or row.get("semi-label")
            toks = convert(text)
            if toks is None:
                stats["dropped"] += 1
                continue
            if args.only_switched and not any(l == "fra" for _, l in toks):
                stats["skipped_monolingual"] += 1
                continue
            stats["sentences"] += 1
            stats["switched"] += any(l == "fra" for _, l in toks)
            for t, l in toks:
                stats[l] += 1
                f.write(f"{t}\t{l}\n")
            f.write("\n")
            if stats["rows"] % 2000 == 0:
                print(f"  ... {stats['rows']} rows")
        # completion marker: lets `cmx_lid.build` tell a finished file from an interrupted one
        f.write(f"# done: {dict(stats)}\n")
    print(f"{args.out}: {dict(stats)}")


if __name__ == "__main__":
    main()
