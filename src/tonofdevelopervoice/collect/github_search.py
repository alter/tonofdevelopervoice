# github_search.py
import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from tonofdevelopervoice.collect.http_retry import fetch_with_retries

GITHUB_API_BASE = "https://api.github.com"
MAX_SEARCH_RESULTS = 1000


def _fetch_page(request: urllib.request.Request) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=45) as response:
        result: dict[str, Any] = json.loads(response.read())
        return result


def search(
    endpoint: str,
    query: str,
    token: str,
    per_page: int = 100,
    sleep: Callable[[float], None] = time.sleep,
    request_timeout: float = 60.0,
    request_interval: float = 2.1,
) -> Iterator[dict[str, Any]]:
    max_pages = MAX_SEARCH_RESULTS // per_page
    executor = ThreadPoolExecutor(max_workers=4)
    try:
        for page in range(1, max_pages + 1):
            url = (
                f"{GITHUB_API_BASE}/search/{endpoint}"
                f"?q={urllib.parse.quote(query)}&per_page={per_page}&page={page}"
            )
            request = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            body = fetch_with_retries(
                executor, request, _fetch_page, sleep=sleep, request_timeout=request_timeout
            )
            items: list[dict[str, Any]] = body.get("items", [])
            if not items:
                return
            yield from items
            if len(items) < per_page:
                return
            sleep(request_interval)
    finally:
        executor.shutdown(wait=False)
