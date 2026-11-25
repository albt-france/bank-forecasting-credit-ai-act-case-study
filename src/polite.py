"""Polite HTTP helper: at most 1 request per second, neutral User-Agent, raw responses cached in data/raw/."""
import time
from pathlib import Path

import requests

USER_AGENT = "bank-ds-case-study/1.0"
MIN_DELAY_S = 1.0
_last = 0.0


def get(url: str, headers: dict | None = None, timeout: int = 90) -> requests.Response:
    global _last
    wait = MIN_DELAY_S - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    h = {"User-Agent": USER_AGENT}
    h.update(headers or {})
    return requests.get(url, headers=h, timeout=timeout)


def cached(url: str, path: Path, headers: dict | None = None) -> tuple[Path, int, bool]:
    """Download url to path unless it is already cached. Returns (path, status, from_cache)."""
    if path.exists() and path.stat().st_size > 0:
        return path, 200, True
    r = get(url, headers)
    if r.status_code == 200:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path, r.status_code, False
