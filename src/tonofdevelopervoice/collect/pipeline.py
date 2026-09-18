# pipeline.py
import json
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from tonofdevelopervoice.collect.filters import is_valid_record


def parse_commit(raw: dict[str, Any], repo: str) -> dict[str, Any]:
    commit = raw["commit"]
    author_date = datetime.fromisoformat(commit["author"]["date"].replace("Z", "+00:00"))
    commit_date = datetime.fromisoformat(commit["committer"]["date"].replace("Z", "+00:00"))
    return {
        "text": commit["message"],
        "source": "commit",
        "repo": repo,
        "sha": raw["sha"],
        "author_date": author_date.isoformat(),
        "commit_date": commit_date.isoformat(),
    }


def filter_records(raw_commits: Iterable[dict[str, Any]], repo: str) -> Iterator[dict[str, Any]]:
    for raw in raw_commits:
        record = parse_commit(raw, repo)
        author_date = datetime.fromisoformat(record["author_date"])
        commit_date = datetime.fromisoformat(record["commit_date"])
        if is_valid_record(author_date, commit_date, record["text"]):
            yield record


def write_jsonl(records: Iterable[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count
