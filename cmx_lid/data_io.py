"""CoNLL-style gold data: `token<TAB>label` per line, blank line between
sentences, `#` starts a comment line."""
from __future__ import annotations

from pathlib import Path

from .schema import LABELS


def read_conll(path: str | Path) -> list[list[tuple[str, str]]]:
    sentences: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip("\n")
        if line.startswith("#"):
            continue
        if not line.strip():
            if current:
                sentences.append(current)
                current = []
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}:{lineno}: expected 'token<TAB>label', got {line!r}")
        tok, label = parts[0], parts[1].strip()
        if label not in LABELS:
            raise ValueError(f"{path}:{lineno}: unknown label {label!r}")
        current.append((tok, label))
    if current:
        sentences.append(current)
    return sentences
