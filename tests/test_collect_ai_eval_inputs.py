# test_collect_ai_eval_inputs.py
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, "scripts")

from collect_ai_eval_inputs import (  # noqa: E402
    collect_raw,
    commit_queries,
    dedup_key_field,
    manifest_for,
    pr_queries,
    run,
    write_jsonl,
)

SEARCH_TARGET = "collect_ai_eval_inputs.search"

AI_COMMIT_MESSAGE = (
    "Improve caching layer for request handler\n\n"
    "This change adds a small in-memory cache in front of the expensive lookup "
    "path, invalidated on write, and adds a metric for the hit rate so we can "
    "see whether it is actually helping in production before expanding it "
    "further. Also documented the new behaviour in the module docstring so the "
    "next reader does not have to guess.\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>"
)

RAW_AI_COMMIT = {
    "sha": "abc123",
    "commit": {
        "author": {"date": "2023-06-01T10:00:00Z"},
        "message": AI_COMMIT_MESSAGE,
    },
    "repository": {"full_name": "octo/widgets"},
}


def test_dedup_key_field_uses_sha_for_commits_and_id_for_issues() -> None:
    assert dedup_key_field("commits") == "sha"
    assert dedup_key_field("issues") == "id"


def test_commit_queries_covers_every_named_agent() -> None:
    queries = commit_queries()
    for agent in ("Claude", "Copilot", "Cursor", "Devin", "aider", "Codex", "Gemini"):
        assert any(agent in q for q in queries)
        assert any("committer-date:>2023-01-01" in q for q in queries)


def test_pr_queries_covers_every_named_agent_and_the_generated_with_query() -> None:
    queries = pr_queries()
    assert any('"Generated with"' in q for q in queries)
    assert all(q.startswith("type:pr ") for q in queries)


def test_collect_raw_dedups_across_queries_by_key_field() -> None:
    def fake_search(_endpoint: str, query: str, _token: str, **_kwargs: Any) -> Any:
        yield RAW_AI_COMMIT
        yield RAW_AI_COMMIT

    with patch(SEARCH_TARGET, side_effect=fake_search):
        items = collect_raw("commits", ["q1", "q2"], "fake-token", sleep=lambda _s: None)
    assert len(items) == 1


def test_write_jsonl_and_manifest_for_report_count_agents_and_min_date(tmp_path: Path) -> None:
    records = [
        {"agent": "Claude", "date": "2023-06-01T10:00:00Z"},
        {"agent": "Claude", "date": "2023-01-01T10:00:00Z"},
        {"agent": "Cursor", "date": "2023-03-01T10:00:00Z"},
    ]
    path = tmp_path / "out.jsonl"
    write_jsonl(records, path)
    manifest = manifest_for(records, path)
    assert manifest["count"] == 3
    assert manifest["agent_counts"] == {"Claude": 2, "Cursor": 1}
    assert manifest["min_date"] == "2023-01-01T10:00:00Z"
    assert manifest["sha256"] is not None


def test_manifest_for_handles_empty_input(tmp_path: Path) -> None:
    manifest = manifest_for([], tmp_path / "missing.jsonl")
    assert manifest == {
        "count": 0,
        "agent_counts": {},
        "min_date": None,
        "sha256": None,
    }


def test_run_writes_both_files_and_a_manifest(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    def fake_search(endpoint: str, _query: str, _token: str, **_kwargs: Any) -> Any:
        if endpoint == "commits":
            yield RAW_AI_COMMIT
        return

    out_dir = tmp_path / "eval_real"
    with patch(SEARCH_TARGET, side_effect=fake_search):
        exit_code = run(["--out-dir", str(out_dir)])

    assert exit_code == 0
    commits = [json.loads(line) for line in (out_dir / "ai_commits.jsonl").read_text().splitlines()]
    assert [c["id"] for c in commits] == ["abc123"]
    assert (out_dir / "ai_prs.jsonl").read_text() == ""
    manifest = json.loads((out_dir / "MANIFEST.json").read_text())
    assert manifest["ai_commits"]["count"] == 1
    assert manifest["ai_prs"]["count"] == 0


def test_run_errors_without_github_token(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)

    exit_code = run(["--out-dir", str(tmp_path / "eval_real")])
    assert exit_code == 1
