"""Command line.

    cmx-lid "n taara l'hôpital kunun"         # colour-free, one line per language run
    cmx-lid                                     # interactive: type sentences, Ctrl+C to quit
    cmx-lid --words "..."                       # one word per line with confidence
    cmx-lid --json < messages.txt               # JSON lines for scripts
    cmx-lid --origins --words "inchallah n taara lekɔli la"

(`cmx-lid` is installed by `pip install -e .`; otherwise use `python -m cmx_lid`.)
"""
from __future__ import annotations

import argparse
import json
import sys

from .pipeline import Identifier
from .summary import segments, summarize

NAMES = {"bam": "Bambara", "fra": "French", "eng": "English"}


def _overview(line: str, tokens) -> str:
    segs = segments(tokens)
    if not segs:
        return "  (no words)"
    runs = "  ".join(f"[{g.label}] {line[g.start:g.end]}" for g in segs)
    s = summarize(tokens)
    share = ", ".join(f"{NAMES[l]} {p:.0%}" for l, p in
                      sorted(s.proportions.items(), key=lambda x: -x[1]))
    mix = f"code-switched, {s.n_switches} switch{'es' if s.n_switches != 1 else ''}" \
        if s.code_switched else "single language"
    return f"{runs}\n  -> {share} ({mix})"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="cmx-lid", description="Which words are Bambara, French or English?")
    ap.add_argument("text", nargs="*", help="text to label (none: read stdin, or interactive)")
    ap.add_argument("--words", "--tokens", action="store_true", dest="words",
                    help="one word per line with label, confidence and deciding stage")
    ap.add_argument("--json", action="store_true", help="JSON lines (one list of tokens per input line)")
    ap.add_argument("--origins", action="store_true",
                    help="with --words/--json: show loanword origin for Bambara words (metadata only)")
    ap.add_argument("--model", default=None, help="classifier file (.json NB or .ftz fastText)")
    ap.add_argument("--summary", action="store_true", help=argparse.SUPPRESS)  # old flag = default view
    args = ap.parse_args(argv)

    try:
        ident = Identifier.load(model_path=args.model) if args.model else Identifier.load()
    except FileNotFoundError as e:
        sys.exit(str(e))
    table = None
    if args.origins:
        from .origins import OriginTable  # the only consumer of the side table
        table = OriginTable.load()

    interactive = not args.text and sys.stdin.isatty()
    if args.text:
        lines = [" ".join(args.text)]
    elif interactive:
        print("Type a sentence and press Enter (Ctrl+C to quit).")
        lines = _prompt()
    else:
        lines = (l.rstrip("\n") for l in sys.stdin)

    for line in lines:
        tokens = ident.identify(line)
        pairs = table.annotate(tokens) if table else [(t, None) for t in tokens]
        if args.json:
            rows = []
            for t, o in pairs:
                d = t.to_dict()
                if table:
                    d["origin"] = o.origin_lang if o else None
                rows.append(d)
            print(json.dumps(rows, ensure_ascii=False))
        elif args.words:
            for t, o in pairs:
                extra = f"  origin={o.origin_lang} ({o.source_form})" if o else ""
                print(f"{t.text:<18} {t.label:<5} {t.confidence:5.2f}  {t.source}{extra}")
            print()
        else:
            print(_overview(line, tokens))
            if interactive:
                print()


def _prompt():
    try:
        while True:
            line = input("> ")
            if line.strip():
                yield line
    except (EOFError, KeyboardInterrupt):
        print()


if __name__ == "__main__":
    main()
