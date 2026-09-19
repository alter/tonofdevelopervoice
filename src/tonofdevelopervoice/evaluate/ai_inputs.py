# ai_inputs.py
import re
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from tonofdevelopervoice.collect.filters import AI_CO_AUTHOR_PATTERN, has_ai_co_author

CUTOFF_2023 = datetime.fromisoformat("2023-01-01T00:00:00+00:00")
COMMIT_MIN_LENGTH = 300
PR_MIN_LENGTH = 500

_GENERATED_WITH_BRACKETED = re.compile(r"(?i)generated with\s*\[([^\]]+)\]")
_GENERATED_WITH_PLAIN = re.compile(r"(?i)generated with\s+([A-Za-z][\w .-]*)")


def extract_generated_with_agent(text: str) -> str | None:
    match = _GENERATED_WITH_BRACKETED.search(text)
    if match:
        return match.group(1).strip()
    match = _GENERATED_WITH_PLAIN.search(text)
    if match:
        return match.group(1).strip()
    return None


def has_generated_with_marker(text: str) -> bool:
    return extract_generated_with_agent(text) is not None


def detect_agent(text: str) -> str | None:
    match = AI_CO_AUTHOR_PATTERN.search(text)
    if match:
        return match.group(1).capitalize()
    return extract_generated_with_agent(text)


def strip_ai_markers(text: str) -> str:
    kept_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.lower().startswith("co-authored-by:") and has_ai_co_author(line):
            continue
        if extract_generated_with_agent(line) is not None:
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines).strip()


def is_eligible(
    text: str, date: datetime, min_length: int, cutoff: datetime = CUTOFF_2023
) -> bool:
    if date < cutoff:
        return False
    if len(text) < min_length:
        return False
    return has_ai_co_author(text) or has_generated_with_marker(text)


def select_with_repo_cap(
    items: Sequence[dict[str, Any]], cap: int = 5, repo_field: str = "repo"
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    seen_text: set[str] = set()
    selected: list[dict[str, Any]] = []
    for item in items:
        text = item["text"]
        if text in seen_text:
            continue
        repo = item[repo_field]
        if counts.get(repo, 0) >= cap:
            continue
        selected.append(item)
        seen_text.add(text)
        counts[repo] = counts.get(repo, 0) + 1
    return selected


def parse_ai_commit(raw: dict[str, Any]) -> dict[str, Any]:
    message = raw["commit"]["message"]
    return {
        "id": raw["sha"],
        "source": "ai_commit",
        "repo": raw["repository"]["full_name"],
        "date": raw["commit"]["author"]["date"],
        "agent": detect_agent(message) or "unknown",
        "text": strip_ai_markers(message),
    }


def parse_ai_pr(raw: dict[str, Any]) -> dict[str, Any]:
    body = raw.get("body") or ""
    repo = "/".join(raw["repository_url"].rstrip("/").split("/")[-2:])
    return {
        "id": f"{repo}#{raw['number']}",
        "source": "ai_pr",
        "repo": repo,
        "date": raw["created_at"],
        "agent": detect_agent(body) or "unknown",
        "text": strip_ai_markers(body),
    }


def select_ai_commits(
    raw_items: Iterable[dict[str, Any]], min_length: int = COMMIT_MIN_LENGTH
) -> Iterable[dict[str, Any]]:
    for raw in raw_items:
        message = raw["commit"]["message"]
        date = datetime.fromisoformat(
            raw["commit"]["author"]["date"].replace("Z", "+00:00")
        )
        if is_eligible(message, date, min_length):
            yield parse_ai_commit(raw)


def select_ai_prs(
    raw_items: Iterable[dict[str, Any]], min_length: int = PR_MIN_LENGTH
) -> Iterable[dict[str, Any]]:
    for raw in raw_items:
        body = raw.get("body") or ""
        date = datetime.fromisoformat(raw["created_at"].replace("Z", "+00:00"))
        if is_eligible(body, date, min_length):
            yield parse_ai_pr(raw)
