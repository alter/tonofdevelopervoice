# github_prs.py
import hashlib
import http.client
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Any

from tonofdevelopervoice.collect.filters import CUTOFF, has_ai_co_author

GITHUB_API_BASE = "https://api.github.com"


def _is_rate_limited(exc: urllib.error.HTTPError) -> bool:
    return exc.code in (403, 429) and exc.headers.get("x-ratelimit-remaining") == "0"


def _rate_limit_wait_seconds(exc: urllib.error.HTTPError) -> float:
    reset_at = exc.headers.get("x-ratelimit-reset")
    if reset_at is None:
        return 60.0
    return max(0.0, float(reset_at) - time.time())


def _fetch_page(request: urllib.request.Request) -> list[dict[str, Any]]:
    with urllib.request.urlopen(request, timeout=45) as response:
        result: list[dict[str, Any]] = json.loads(response.read())
        return result


def fetch_pull_requests(
    repo: str,
    token: str,
    before: str,
    per_page: int = 100,
    start_page: int = 1,
    max_pages: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    request_timeout: float = 60.0,
) -> Iterator[tuple[int, list[dict[str, Any]]]]:
    page = start_page
    pages_fetched = 0
    executor = ThreadPoolExecutor(max_workers=4)
    try:
        while max_pages is None or pages_fetched < max_pages:
            url = (
                f"{GITHUB_API_BASE}/repos/{repo}/pulls"
                f"?state=closed&sort=created&direction=asc&per_page={per_page}&page={page}"
            )
            request = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            transient_attempts = 0
            while True:
                try:
                    batch = executor.submit(_fetch_page, request).result(timeout=request_timeout)
                    break
                except FutureTimeoutError as exc:
                    if transient_attempts < 3:
                        transient_attempts += 1
                        sleep(2.0**transient_attempts)
                        continue
                    raise RuntimeError(
                        f"GitHub API request timed out after {request_timeout}s (page {page})"
                    ) from exc
                except urllib.error.HTTPError as exc:
                    if _is_rate_limited(exc):
                        sleep(_rate_limit_wait_seconds(exc))
                        continue
                    if 500 <= exc.code < 600 and transient_attempts < 3:
                        transient_attempts += 1
                        sleep(2.0**transient_attempts)
                        continue
                    raise RuntimeError(
                        f"GitHub API request failed: {exc.code} {exc.reason}"
                    ) from exc
                except (urllib.error.URLError, http.client.HTTPException, TimeoutError) as exc:
                    if transient_attempts < 3:
                        transient_attempts += 1
                        sleep(2.0**transient_attempts)
                        continue
                    raise RuntimeError(f"GitHub API request failed: {exc}") from exc

            if not batch:
                return

            cutoff_hit = False
            kept: list[dict[str, Any]] = []
            for pr in batch:
                if pr["created_at"] >= before:
                    cutoff_hit = True
                    break
                kept.append(pr)

            yield page, kept
            pages_fetched += 1
            if cutoff_hit or len(batch) < per_page:
                return
            page += 1
    finally:
        executor.shutdown(wait=False)


def is_valid_pull_request(raw: dict[str, Any], cutoff: datetime = CUTOFF) -> bool:
    if raw.get("merged_at") is None:
        return False
    created_at = datetime.fromisoformat(raw["created_at"].replace("Z", "+00:00"))
    if created_at >= cutoff:
        return False
    user = raw.get("user") or {}
    if user.get("type") != "User":
        return False
    login = user.get("login", "")
    if login.endswith("[bot]"):
        return False
    body = raw.get("body")
    if not body or not body.strip():
        return False
    if has_ai_co_author(body):
        return False
    return True


def parse_pull_request(raw: dict[str, Any], repo: str) -> dict[str, Any]:
    login = (raw.get("user") or {}).get("login", "")
    title = raw.get("title") or ""
    body = raw.get("body") or ""
    return {
        "id": f"{repo}#{raw['number']}",
        "source": "pr",
        "repo": repo,
        "text": f"{title}\n\n{body}",
        "author_date": raw["created_at"],
        "author_hash": hashlib.sha256(login.encode("utf-8")).hexdigest()[:12],
    }


def filter_pull_requests(
    raw_prs: Iterable[dict[str, Any]], repo: str, cutoff: datetime = CUTOFF
) -> Iterator[dict[str, Any]]:
    for raw in raw_prs:
        if is_valid_pull_request(raw, cutoff):
            yield parse_pull_request(raw, repo)
