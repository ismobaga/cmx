"""Minimal Hugging Face client, stdlib only (pyarrow optional).

Two ways to read a dataset:
  * parquet (preferred): one download per split via the Hub's auto-converted
    parquet files. Few requests, so no rate limiting. Needs `pip install pyarrow`.
  * rows API: pages of 100 rows from datasets-server. No extra dependency, but
    many requests, and HF answers 429 Too Many Requests on bigger datasets.

Gated datasets need $HF_TOKEN from an account that was granted access.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterator, Sequence

API = "https://datasets-server.huggingface.co/rows"
SPLITS_API = "https://datasets-server.huggingface.co/splits"
HUB = "https://huggingface.co/api/datasets"
RETRY_CODES = (429, 500, 502, 503, 504)


def _headers(auth: bool = True) -> dict:
    h = {"User-Agent": "cmx-lid-ingest"}
    token = os.environ.get("HF_TOKEN")
    if auth and token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _wait_for(e: urllib.error.HTTPError, delay: float) -> float:
    ra = e.headers.get("Retry-After") if e.headers else None
    try:
        return max(float(ra), delay) if ra else delay
    except ValueError:
        return delay


def _open(url: str, retries: int = 8, auth: bool = True) -> bytes:
    """GET with retries. 429/5xx back off exponentially (2s .. ~4 min), honouring Retry-After."""
    delay = 2.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=_headers(auth)),
                                        timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in RETRY_CODES and attempt < retries - 1:
                wait = _wait_for(e, delay)
                print(f"  HTTP {e.code}, retrying in {wait:.0f}s ...", file=sys.stderr)
                time.sleep(wait)
                delay = min(delay * 2, 240)
                continue
            if e.code in (401, 403):
                raise PermissionError(
                    f"HTTP {e.code} for {url}: set HF_TOKEN from an account that has "
                    "accepted this dataset's conditions") from e
            raise
        except urllib.error.URLError:
            if attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 240)
                continue
            raise
    raise RuntimeError("unreachable")


def _get_json(url: str) -> dict:
    return json.loads(_open(url))


# --- parquet path ------------------------------------------------------------

def parquet_urls(dataset: str) -> dict[str, dict[str, list[str]]]:
    """{config: {split: [parquet urls]}} from the Hub's auto-converted files."""
    return _get_json(f"{HUB}/{dataset}/parquet")


def _is_hub(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.split(":")[0]
    return host == "huggingface.co" or host.endswith(".huggingface.co") and not host.startswith("cdn")


def _download(url: str, max_hops: int = 5) -> bytes:
    """Follow redirects by hand: the token goes to huggingface.co only, never to
    the signed CDN URL (which can reject a second auth mechanism)."""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    delay, attempt = 2.0, 0
    for _ in range(max_hops + 8):
        auth = _is_hub(url)
        try:
            with opener.open(urllib.request.Request(url, headers=_headers(auth)), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.parse.urljoin(url, e.headers["Location"])
                continue
            if e.code in RETRY_CODES and attempt < 7:
                attempt += 1
                wait = _wait_for(e, delay)
                print(f"  HTTP {e.code}, retrying in {wait:.0f}s ...", file=sys.stderr)
                time.sleep(wait)
                delay = min(delay * 2, 240)
                continue
            if e.code in (401, 403):
                raise PermissionError(f"HTTP {e.code}: HF_TOKEN missing or access not granted") from e
            raise
    raise RuntimeError(f"too many redirects for {url}")


def read_parquet_rows(data: bytes, columns: Sequence[str] | None = None) -> Iterator[dict]:
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as e:
        raise ImportError("parquet download needs `pip install pyarrow` (or use --via rows)") from e
    table = pq.read_table(io.BytesIO(data), columns=list(columns) if columns else None)
    yield from table.to_pylist()


def iter_hf_parquet(dataset: str, config: str | None = None, split: str | None = None,
                    columns: Sequence[str] | None = None, limit: int | None = None) -> Iterator[dict]:
    """Rows of every (config, split), or only the ones asked for."""
    n = 0
    for cfg, splits in parquet_urls(dataset).items():
        if config and cfg != config:
            continue
        for sp, urls in splits.items():
            if split and split != "all" and sp != split:
                continue
            print(f"  {cfg}/{sp}: {len(urls)} parquet file(s)", file=sys.stderr)
            for url in urls:
                for row in read_parquet_rows(_download(url), columns):
                    yield row
                    n += 1
                    if limit is not None and n >= limit:
                        return


# --- rows API path -------------------------------------------------------------

def list_splits(dataset: str) -> list[tuple[str, str]]:
    """[(config, split), ...] for a dataset (gated ones need HF_TOKEN)."""
    q = urllib.parse.urlencode({"dataset": dataset})
    data = _get_json(f"{SPLITS_API}?{q}")
    return [(s["config"], s["split"]) for s in data.get("splits", [])]


def iter_hf_rows(dataset: str, config: str, split: str, columns: Sequence[str] | None = None,
                 limit: int | None = None, page: int = 100, pause: float = 1.0) -> Iterator[dict]:
    offset = 0
    while limit is None or offset < limit:
        n = page if limit is None else min(page, limit - offset)
        q = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split,
                                    "offset": offset, "length": n})
        data = _get_json(f"{API}?{q}")
        rows = data.get("rows", [])
        if not rows:
            return
        for r in rows:
            row = r["row"]
            yield {k: row.get(k) for k in columns} if columns else row
        offset += len(rows)
        if offset >= data.get("num_rows_total", float("inf")):
            return
        time.sleep(pause)


def pyarrow_available() -> bool:
    try:
        import pyarrow.parquet  # noqa: F401
        return True
    except ImportError:
        return False


def iter_jsonl(path: str | Path, limit: int | None = None) -> Iterator[dict]:
    """Offline path: rows exported with e.g. `datasets` -> .to_json(lines=True)."""
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                return
            if line.strip():
                yield json.loads(line)
