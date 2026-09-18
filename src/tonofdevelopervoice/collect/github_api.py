# github_api.py
import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

GITHUB_API_BASE = "https://api.github.com"


def fetch_commits(
    repo: str,
    token: str,
    until: str,
    per_page: int = 100,
    max_pages: int | None = None,
) -> Iterator[dict[str, Any]]:
    page = 1
    while max_pages is None or page <= max_pages:
        url = (
            f"{GITHUB_API_BASE}/repos/{repo}/commits"
            f"?until={until}&per_page={per_page}&page={page}"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request) as response:
                batch: list[dict[str, Any]] = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"GitHub API request failed: {exc.code} {exc.reason}") from exc

        if not batch:
            return
        yield from batch
        if len(batch) < per_page:
            return
        page += 1
