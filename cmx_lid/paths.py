"""Resource locations.

Two layouts:
  * a checkout of the repo (development): data/ and models/ next to cmx_lid/
  * an installed package (pip install cmx-lid): the model, lexicon and origin
    table ship inside cmx_lid/resources/

Loading uses the repo files when they exist, otherwise the packaged copies.
Training and data tools always write into the repo. Override the repo root
with $CMX_LID_HOME.
"""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_RESOURCES = Path(__file__).resolve().parent / "resources"
ROOT = Path(os.environ.get("CMX_LID_HOME", Path(__file__).resolve().parent.parent))
DATA_DIR = ROOT / "data"
TRAIN_PATH = DATA_DIR / "seed" / "train.conll"
DEV_PATH = DATA_DIR / "seed" / "dev.conll"
# where training writes the Naive Bayes model (repo only)
TRAIN_MODEL_PATH = ROOT / "models" / "cmx-lid-nb.json"


def resource(name: str) -> Path:
    """A data file by name: the repo's data/ or models/ copy if present, else the packaged one."""
    for candidate in (DATA_DIR / name, ROOT / "models" / name):
        if candidate.exists():
            return candidate
    return PACKAGE_RESOURCES / name


LEXICON_PATH = resource("lexicon.tsv")
MODEL_PATH = resource("cmx-lid-nb.json")
