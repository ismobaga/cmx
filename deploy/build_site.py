"""Assemble the static site locally, the same way the Dockerfile does.

    python deploy/build_site.py                 # -> site-dist/
    python -m http.server 8080 -d site-dist      # preview at http://localhost:8080/lid/

Needs the JS runtime compiled once:  cd js && npm install
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site-dist"

# module name -> folder holding its compiled dist/ and model/
MODULES = {"cmx-lid": ROOT / "js"}


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)  # leftovers are simply overwritten below
    shutil.copytree(ROOT / "site", out, dirs_exist_ok=True)
    for name, src in MODULES.items():
        if not (src / "dist" / "index.js").exists():
            sys.exit(f"{src / 'dist'} missing: run `npm install` in {src}")
        shutil.copytree(src / "dist", out / "vendor" / name / "dist", dirs_exist_ok=True)
        shutil.copytree(src / "model", out / "vendor" / name / "model", dirs_exist_ok=True)
    print(f"site built in {out}\npreview: python -m http.server 8080 -d {out.name}  ->  http://localhost:8080/")


if __name__ == "__main__":
    main()
