# test_collector.py
import json
import urllib.error
from email.message import Message
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tonofdevelopervoice.collect.github_api import fetch_commits
from tonofdevelopervoice.collect.pipeline import filter_records, parse_commit, write_jsonl

RAW_COMMIT_VALID = {
    "sha": "abc123",
    "commit": {
        "author": {"date": "2019-05-01T10:00:00Z"},
        "committer": {"date": "2019-05-02T10:00:00Z"},
        "message": "fix null pointer dereference in handler",
    },
}

RAW_COMMIT_TOO_RECENT = {
    "sha": "def456",
    "commit": {
        "author": {"date": "2022-01-01T10:00:00Z"},
        "committer": {"date": "2022-01-01T10:00:00Z"},
        "message": "add feature flag",
    },
}

URLOPEN_TARGET = "tonofdevelopervoice.collect.github_api.urllib.request.urlopen"

RAW_COMMIT_AI_CO_AUTHOR = {
    "sha": "ghi789",
    "commit": {
        "author": {"date": "2020-01-01T10:00:00Z"},
        "committer": {"date": "2020-01-01T10:00:00Z"},
        "message": "fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
    },
}


def test_parse_commit_extracts_expected_fields() -> None:
    record = parse_commit(RAW_COMMIT_VALID, repo="linux")
    assert record["text"] == "fix null pointer dereference in handler"
    assert record["source"] == "commit"
    assert record["repo"] == "linux"
    assert record["sha"] == "abc123"
    assert record["author_date"].startswith("2019-05-01")
    assert record["commit_date"].startswith("2019-05-02")


def test_filter_records_keeps_only_valid_commits() -> None:
    raw = [RAW_COMMIT_VALID, RAW_COMMIT_TOO_RECENT, RAW_COMMIT_AI_CO_AUTHOR]
    kept = list(filter_records(raw, repo="linux"))
    assert len(kept) == 1
    assert kept[0]["sha"] == "abc123"


def test_write_jsonl_creates_parent_dirs_and_writes_lines(tmp_path: Path) -> None:
    out = tmp_path / "raw" / "linux.jsonl"
    records: list[dict[str, Any]] = [{"sha": "a"}, {"sha": "b"}]
    count = write_jsonl(records, out)
    assert count == 2
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"sha": "a"}
    assert json.loads(lines[1]) == {"sha": "b"}


def test_fetch_commits_paginates_until_short_page() -> None:
    page1 = [RAW_COMMIT_VALID] * 2
    page2 = [RAW_COMMIT_TOO_RECENT]

    responses = [page1, page2]

    def fake_urlopen(_request: Any) -> MagicMock:
        body = json.dumps(responses.pop(0)).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = body
        return cm

    with patch(URLOPEN_TARGET, side_effect=fake_urlopen):
        commits = list(
            fetch_commits("owner/repo", "fake-token", "2021-01-01T00:00:00Z", per_page=2)
        )

    assert len(commits) == 3


def test_fetch_commits_stops_at_max_pages() -> None:
    page = [RAW_COMMIT_VALID] * 2

    def fake_urlopen(_request: Any) -> MagicMock:
        body = json.dumps(page).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = body
        return cm

    with patch(URLOPEN_TARGET, side_effect=fake_urlopen):
        commits = list(
            fetch_commits(
                "owner/repo", "fake-token", "2021-01-01T00:00:00Z", per_page=2, max_pages=1
            )
        )

    assert len(commits) == 2


def test_fetch_commits_stops_on_empty_page() -> None:
    def fake_urlopen(_request: Any) -> MagicMock:
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = b"[]"
        return cm

    with patch(URLOPEN_TARGET, side_effect=fake_urlopen):
        commits = list(fetch_commits("owner/repo", "fake-token", "2021-01-01T00:00:00Z"))

    assert commits == []


def test_fetch_commits_raises_runtime_error_on_http_error() -> None:
    def fake_urlopen(_request: Any) -> MagicMock:
        raise urllib.error.HTTPError(
            url="https://api.github.com", code=403, msg="Forbidden", hdrs=Message(), fp=None
        )

    with (
        patch(URLOPEN_TARGET, side_effect=fake_urlopen),
        pytest.raises(RuntimeError, match="403"),
    ):
        list(fetch_commits("owner/repo", "fake-token", "2021-01-01T00:00:00Z"))
