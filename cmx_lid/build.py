"""Build cmx-lid from public data in one command.

    python -m cmx_lid.build                 # download what's missing, train, benchmark
    python -m cmx_lid.build --fasttext      # also train the optional fastText model
    python -m cmx_lid.build --no-hf         # skip Hugging Face (Kunkado, djelia)
    python -m cmx_lid.build --refresh       # re-download everything

Steps (each is skipped if its output already exists, unless --refresh):
  1. BAYƐLƐMABAGA (GitHub) + English word frequencies (GitHub)
  2. Kunkado radio transcripts (Hugging Face, open; slow: ~10 min)
  3. djelia/bambara-mt-dataset (Hugging Face, gated; only if HF_TOKEN is set)
  4. word lists -> train the model (Naive Bayes; fastText with --fasttext)
  5. benchmark on held-out data; results in models/report.json
  +  export the model for the JavaScript package (js/), if present

Anything that can't be downloaded is skipped with a note; the build still finishes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import paths

RAW = paths.DATA_DIR / "raw"
SILVER = paths.DATA_DIR / "silver"
BAYE = RAW / "bayelemabaga"
BAYE_URL = "https://raw.githubusercontent.com/RobotsMali-AI/datasets/HEAD/bayelemabaga"
BAYE_FILES = ["train/train.bam", "train/train.fr", "valid/dev.bam", "valid/dev.fr",
              "test/test.bam", "test/test.fr", "LICENSE"]
FREQ = RAW / "frequencywords" / "en_50k.txt"
FREQ_URL = ("https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/"
            "content/2018/en/en_50k.txt")

WL_BAYE = SILVER / "wl-bayelemabaga.tsv"
WL_EN = SILVER / "wl-en-top10k.tsv"
WL_DJELIA = SILVER / "wl-djelia.tsv"
KUNKADO_TRAIN = SILVER / "kunkado-train.conll"
KUNKADO_TEST = SILVER / "kunkado-test.conll"
REPORT = paths.ROOT / "models" / "report.json"


def say(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str, dest: Path, refresh: bool) -> bool:
    if dest.exists() and dest.stat().st_size > 0 and not refresh:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cmx-lid-build"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            return True
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                say(f"    could not download {url}: {e}")
                return False
            time.sleep(3)
    return False


def hf_reachable() -> bool:
    try:
        urllib.request.urlopen(urllib.request.Request(
            "https://huggingface.co/api/datasets/RobotsMali/kunkado",
            headers={"User-Agent": "cmx-lid-build"}), timeout=15).close()
        return True
    except Exception:
        return False


def fresh(path: Path, refresh: bool) -> bool:
    return path.exists() and path.stat().st_size > 0 and not refresh


def complete_conll(path: Path) -> bool:
    """Kunkado files end with '# done: ...' when the download finished."""
    try:
        with open(path, "rb") as f:
            f.seek(max(0, path.stat().st_size - 400))
            return b"# done:" in f.read()
    except OSError:
        return False


def sync_package_resources() -> None:
    """Copy the freshly trained model + lexicon + origin table into cmx_lid/resources/,
    so `pip install cmx-lid` ships the same model the build just benchmarked."""
    import shutil
    dest = paths.PACKAGE_RESOURCES
    dest.mkdir(parents=True, exist_ok=True)
    for src in (paths.TRAIN_MODEL_PATH, paths.DATA_DIR / "lexicon.tsv",
                paths.DATA_DIR / "loanword_origin.tsv"):
        if src.exists():
            shutil.copyfile(src, dest / src.name)
    say(f"[+] Package resources updated in {dest.relative_to(paths.ROOT)}/")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fasttext", action="store_true", help="also train models/cmx-lid-ft.ftz")
    ap.add_argument("--no-hf", action="store_true", help="skip Hugging Face downloads")
    ap.add_argument("--refresh", action="store_true", help="re-download and rebuild everything")
    ap.add_argument("--skip-benchmark", action="store_true")
    args = ap.parse_args(argv)
    t0 = time.time()

    # 1 -------------------------------------------------------------------
    say("[1/5] Public text from GitHub")
    ok_baye = all(fetch(f"{BAYE_URL}/{f}", BAYE / f, args.refresh) for f in BAYE_FILES)
    ok_freq = fetch(FREQ_URL, FREQ, args.refresh)
    say(f"    BAYƐLƐMABAGA: {'ok' if ok_baye else 'MISSING'}   English words: {'ok' if ok_freq else 'MISSING'}")
    if not ok_baye:
        sys.exit("BAYƐLƐMABAGA is required (it is the main training and test data). "
                 "Check your internet connection and run again.")

    # 2-3 -----------------------------------------------------------------
    use_hf = not args.no_hf and hf_reachable()
    if not args.no_hf and not use_hf:
        say("[2/5] Hugging Face not reachable: skipping Kunkado and djelia")
    elif args.no_hf:
        say("[2/5] Skipping Hugging Face (--no-hf)")
    if use_hf:
        from .ingest import kunkado
        say("[2/5] Kunkado radio transcripts (real code-switching)")
        for split, out in (("test", KUNKADO_TEST), ("train", KUNKADO_TRAIN)):
            if fresh(out, args.refresh) and complete_conll(out):
                say(f"    {split}: already downloaded ({out.name})")
                continue
            if out.exists() and not args.refresh:
                say(f"    {split}: previous download looks incomplete, fetching again")
            say(f"    {split}: downloading (the train split takes ~10 min) ...")
            try:
                kunkado.main(["--split", split, "--out", str(out)])
            except Exception as e:
                say(f"    {split}: failed ({e}); continuing without it")
        say("[3/5] djelia/bambara-mt-dataset (gated)")
        if fresh(WL_DJELIA, args.refresh):
            say("    already built")
        elif not os.environ.get("HF_TOKEN"):
            say("    skipped: set HF_TOKEN (an account with access) to include it")
        else:
            from .ingest import wordlist
            try:
                wordlist.main(["--hf", "djelia/bambara-mt-dataset", "--split", "all",
                               "--out", str(WL_DJELIA)])
            except (Exception, SystemExit) as e:
                say(f"    failed ({e}); continuing without it")
    else:
        say("[3/5] djelia skipped")

    # 4 -------------------------------------------------------------------
    say("[4/5] Word lists and training")
    from .ingest import wordlist
    if not fresh(WL_BAYE, args.refresh):
        wordlist.main(["--text", f"bam={BAYE / 'train/train.bam'}",
                       "--text", f"fra={BAYE / 'train/train.fr'}", "--out", str(WL_BAYE)])
    if ok_freq and not fresh(WL_EN, args.refresh):
        wordlist.main(["--freq", f"eng={FREQ}", "--limit", "10000", "--out", str(WL_EN)])
    data = []
    for wl in (WL_BAYE, WL_EN, WL_DJELIA):
        if wl.exists():
            data += ["--wordlist", str(wl)]
    if KUNKADO_TRAIN.exists():
        data += ["--conll", str(KUNKADO_TRAIN)]
    say("    using: " + ", ".join(Path(x).name for x in data[1::2]))
    from . import train
    train.main(data)
    if args.fasttext:
        if importlib.util.find_spec("fasttext"):
            train.main(data + ["--backend", "fasttext"])
        else:
            say("    fastText skipped: pip install fasttext-wheel")

    # 5 -------------------------------------------------------------------
    report = {"built": time.strftime("%Y-%m-%d %H:%M"), "training_data": data[1::2]}
    if not args.skip_benchmark:
        say("[5/5] Benchmark (held-out data, never trained on)")
        from . import benchmark, evaluate
        from .data_io import read_conll
        from .pipeline import Identifier
        models = {"nb": paths.TRAIN_MODEL_PATH}
        ft = paths.ROOT / "models" / "cmx-lid-ft.ftz"
        if args.fasttext and ft.exists():
            models["fasttext"] = ft
        for name, path in models.items():
            ident = Identifier.load(model_path=path)
            res = benchmark.run(ident, "test")
            benchmark.print_table(res, f"  {name}: BAYƐLƐMABAGA test")
            entry = {"bayelemabaga_test": res}
            if KUNKADO_TEST.exists():
                k = evaluate.evaluate(ident, read_conll(KUNKADO_TEST))
                f = k["per_label"].get("fra", {})
                say(f"  {name}: Kunkado test (real code-switching): accuracy {k['accuracy']:.3f}, "
                    f"French F1 {f.get('f1', 0):.3f} (P {f.get('p', 0):.2f} R {f.get('r', 0):.2f})")
                entry["kunkado_test"] = {kk: v for kk, v in k.items() if kk != "errors"}
            report[name] = entry
    sync_package_resources()
    js_dir = paths.ROOT / "js"
    if js_dir.exists():
        say("[+] JavaScript package: exporting model to js/model/cmx-lid.json")
        from . import export_js
        export_js.main([])
        say("    run `npm test` in js/ to confirm the JS port still matches")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    say(f"\nDone in {(time.time() - t0) / 60:.1f} min. Model: {paths.TRAIN_MODEL_PATH.name}; "
        f"report: models/{REPORT.name}\nTry it:  python -m cmx_lid \"n taara l'hôpital kunun\"")


if __name__ == "__main__":
    main()
