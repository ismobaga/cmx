"""Export the trained model for the JavaScript/TypeScript package (js/).

    python -m cmx_lid.export_js            # writes js/model/cmx-lid.json + js/test fixtures

The bundle holds everything the JS runtime needs (lexicon, Naive Bayes counts,
router character tables, pipeline config), so Python stays the single source
of truth. `python -m cmx_lid.build` runs this automatically when js/ exists.
Only the Naive Bayes model can be exported (fastText has no JS runtime here).
"""
from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import asdict
from pathlib import Path

from . import paths, router, tokenize as tk
from .augment import informalize
from .classifier import CharNgramNB
from .lexicon import Lexicon
from .normalize import _APOSTROPHES, _OLD_ORTHOGRAPHY
from .pipeline import _SENTENCE_END, Config, Identifier
from .schema import LABELS, LANG_LABELS, SCHEMA_VERSION
from .summary import summarize

JS_DIR = paths.ROOT / "js"
FORMAT = "cmx-lid-js/1"


def _prune(model: CharNgramNB, min_count: int):
    grams = {}
    for i, l in enumerate(model.labels):
        for g, n in model.counts[l].items():
            grams.setdefault(g, [0] * len(model.labels))[i] = n
    if min_count > 1:
        grams = {g: c for g, c in grams.items() if sum(c) >= min_count}
        totals = [sum(c[i] for c in grams.values()) for i in range(len(model.labels))]
        vocab = len(grams)
    else:
        totals = [model.totals[l] for l in model.labels]
        vocab = model.vocab_size
    return grams, totals, vocab


def build_bundle(model_path=paths.TRAIN_MODEL_PATH, lexicon_path=paths.LEXICON_PATH,
                 prune: int = 1) -> dict:
    if Path(model_path).suffix != ".json":
        raise SystemExit("only the Naive Bayes (.json) model can be exported to JS")
    model = CharNgramNB.load(model_path)
    lex = Lexicon.load(lexicon_path)
    grams, totals, vocab = _prune(model, prune)
    return {
        "format": FORMAT,
        "version": __import__("cmx_lid").__version__,
        "schema_version": SCHEMA_VERSION,
        "labels": list(LABELS),
        "lang_labels": list(LANG_LABELS),
        "config": asdict(Config()),
        "rules": {
            "apostrophes": {chr(k): v for k, v in _APOSTROPHES.items()},
            "old_orthography": {chr(k): v for k, v in _OLD_ORTHOGRAPHY.items()},
            "bam_letters": "".join(sorted(router.BAM_LETTERS)),
            "bam_tone_vowels": "".join(sorted(router.BAM_TONE_VOWELS)),
            "fra_marks": "".join(sorted(router.FRA_MARKS)),
            "fra_clitics": sorted(router.FRA_CLITICS),
            "bam_clitics": sorted(router.BAM_CLITICS),
            "en_contraction_suffixes": sorted(tk._EN_CONTRACTION_SUFFIXES),
            "sentence_end": sorted(_SENTENCE_END),
        },
        "lexicon": {form: w for form, w in lex._entries.items()},
        "model": {
            "labels": list(model.labels), "n_min": model.n_min, "n_max": model.n_max,
            "alpha": model.alpha, "temp_power": model.temp_power, "vocab_size": vocab,
            "log_priors": [model.log_priors[l] for l in model.labels],
            "totals": totals, "grams": grams,
        },
    }


SPECIAL = [
    "n taara l'hôpital kunun", "n taara opital la", "n taara hôpital la",
    "inchallah, n bɛ na sini", "al-hamdoulillah an bɛɛ ka kɛnɛ", "n bè taa sugu la",
    "meeting in bɛ kɛ tomorrow at 10", "c'est vrai, a ko ten", "k'a fɔ ko n tɛ se",
    "réunion bɛ kɛ demain 🙂 https://yanmali.com @moussa #Bamako",
    "Tilayɔrɔ IV ni VII", "n ye Kulubali ye sugu la", "Ala ka an kisi الحمد لله",
    "ߒ ߓߍ߫ ߕߊ߯", "I ka kɛnɛ wa ?", "it's okay, we're fine", "aujourd'hui insha'allah",
    "L’école bɛ daminɛ sini", "bɛ́ taa", "a ye tche ye dougou kono", "", "... 123 🙂",
    "Je suis fatigué, n tɛ se ka na. The weather is nice!",
]


def fixtures(ident: Identifier, n_real: int = 250, seed: int = 7) -> list[dict]:
    from .benchmark import load_pairs
    rng = random.Random(seed)
    texts = list(SPECIAL)
    try:
        pairs = load_pairs("test")[:n_real]
        texts += [b for b, _ in pairs] + [f for _, f in pairs[:100]]
        texts += [informalize(b, rng) for b, _ in pairs[:100]]
        for b, f in pairs[:100]:
            fw, bw = f.split(), b.split()
            if len(bw) > 1 and fw:
                cut = rng.randrange(1, len(bw))
                texts.append(" ".join(bw[:cut] + fw[:2] + bw[cut:]))
    except FileNotFoundError:
        pass
    kt = paths.DATA_DIR / "silver" / "kunkado-test.conll"
    if kt.exists():
        from .data_io import read_conll
        texts += [" ".join(w for w, _ in s) for s in read_conll(kt)[:150]]
    out = []
    for t in texts:
        toks = ident.identify(t)
        s = summarize(toks)
        out.append({"text": t,
                    "tokens": [[x.text, x.label, x.confidence, x.source] for x in toks],
                    "dominant": s.dominant, "code_switched": s.code_switched,
                    "n_switches": s.n_switches})
    return out


def char_classes() -> dict:
    """Code-point ranges Python's regex classes match, to check the JS equivalents."""
    def ranges(pat):
        rx, out, start = re.compile(pat), [], None
        for cp in range(0x110000):
            hit = bool(rx.match(chr(cp)))
            if hit and start is None:
                start = cp
            elif not hit and start is not None:
                out.append([start, cp - 1]); start = None
        if start is not None:
            out.append([start, 0x10FFFF])
        return out
    import unicodedata
    unassigned, start = [], None
    for cp in range(0x110000):
        hit = unicodedata.category(chr(cp)) == "Cn"
        if hit and start is None:
            start = cp
        elif not hit and start is not None:
            unassigned.append([start, cp - 1]); start = None
    if start is not None:
        unassigned.append([start, 0x10FFFF])
    return {"letter": ranges(r"[^\W\d_]"), "word": ranges(r"\w"), "digit": ranges(r"\d"),
            "unassigned": unassigned, "unicode_version": unicodedata.unidata_version}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=paths.TRAIN_MODEL_PATH)
    ap.add_argument("--prune", type=int, default=1,
                    help="drop n-grams seen fewer times (smaller bundle, slightly different output)")
    ap.add_argument("--out", default=JS_DIR / "model" / "cmx-lid.json")
    ap.add_argument("--no-fixtures", action="store_true")
    args = ap.parse_args(argv)

    bundle = build_bundle(args.model, prune=args.prune)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"JS bundle: {out} ({out.stat().st_size // 1024} KB, {len(bundle['model']['grams'])} n-grams)")
    if not args.no_fixtures and args.prune == 1:
        test_dir = JS_DIR / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        fx = fixtures(Identifier.load(model_path=args.model))
        (test_dir / "fixtures.json").write_text(json.dumps(fx, ensure_ascii=False), encoding="utf-8")
        (test_dir / "charclass.json").write_text(json.dumps(char_classes()), encoding="utf-8")
        print(f"parity fixtures: {len(fx)} texts")


if __name__ == "__main__":
    main()
