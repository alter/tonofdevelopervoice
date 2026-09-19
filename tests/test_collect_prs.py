# test_collect_prs.py
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, "scripts")

from collect_prs import (  # noqa: E402
    candidate_paths,
    collect_repo_candidates,
    load_candidates,
    repo_manifest,
)

FETCH_TARGET = "collect_prs.fetch_pull_requests"

RAW_PR_A = {
    "number": 1,
    "created_at": "2019-05-01T10:00:00Z",
    "merged_at": "2019-05-02T10:00:00Z",
    "user": {"login": "alice", "type": "User"},
    "title": "Fix A",
    "body": "Fixes A for real.",
}
RAW_PR_B = {
    "number": 2,
    "created_at": "2019-06-01T10:00:00Z",
    "merged_at": "2019-06-02T10:00:00Z",
    "user": {"login": "bob", "type": "User"},
    "title": "Fix B",
    "body": "Fixes B for real.",
}


def test_collect_repo_candidates_writes_filtered_records(tmp_path: Path) -> None:
    def fake_fetch(*_args: Any, **_kwargs: Any) -> Any:
        yield 1, [RAW_PR_A, RAW_PR_B]

    with patch(FETCH_TARGET, side_effect=fake_fetch):
        path = collect_repo_candidates("owner/repo", "fake-token", tmp_path)

    records = load_candidates(path)
    assert [r["id"] for r in records] == ["repo#1", "repo#2"]


def test_collect_repo_candidates_resumes_from_checkpoint_without_duplicating(
    tmp_path: Path,
) -> None:
    def fake_fetch_page_1(*_args: Any, start_page: int = 1, **_kwargs: Any) -> Any:
        assert start_page == 1
        yield 1, [RAW_PR_A]

    with patch(FETCH_TARGET, side_effect=fake_fetch_page_1):
        first_path = collect_repo_candidates("owner/repo", "fake-token", tmp_path)
    assert [r["id"] for r in load_candidates(first_path)] == ["repo#1"]

    def fake_fetch_page_2(*_args: Any, start_page: int = 1, **_kwargs: Any) -> Any:
        assert start_page == 2
        yield 2, [RAW_PR_B]

    with patch(FETCH_TARGET, side_effect=fake_fetch_page_2):
        second_path = collect_repo_candidates("owner/repo", "fake-token", tmp_path)

    records = load_candidates(second_path)
    assert [r["id"] for r in records] == ["repo#1", "repo#2"]


def test_candidate_paths_creates_the_candidates_directory(tmp_path: Path) -> None:
    candidates_path, checkpoint_path = candidate_paths(tmp_path, "repo")
    assert candidates_path.parent == checkpoint_path.parent
    assert candidates_path.parent.is_dir()


def test_load_candidates_returns_empty_list_when_file_is_missing(tmp_path: Path) -> None:
    assert load_candidates(tmp_path / "missing.jsonl") == []


def test_load_candidates_survives_a_unicode_line_separator_inside_a_field(
    tmp_path: Path,
) -> None:
    path = tmp_path / "candidates.jsonl"
    text_with_u2028 = "line one" + chr(0x2028) + "line two"
    record_with_u2028 = {
        "id": "repo#1",
        "author_date": "2019-01-01T00:00:00Z",
        "author_hash": "a",
        "text": text_with_u2028,
    }
    other = {"id": "repo#2", "author_date": "2019-02-01T00:00:00Z", "author_hash": "b"}
    path.write_text(
        json.dumps(record_with_u2028, ensure_ascii=False)
        + "\n"
        + json.dumps(other, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    records = load_candidates(path)
    assert [r["id"] for r in records] == ["repo#1", "repo#2"]
    assert records[0]["text"] == text_with_u2028


def test_load_candidates_deduplicates_by_id_keeping_the_first_occurrence(
    tmp_path: Path,
) -> None:
    path = tmp_path / "candidates.jsonl"
    rec_a1 = {"id": "repo#1", "author_date": "2019-01-01T00:00:00Z", "author_hash": "a"}
    rec_b = {"id": "repo#2", "author_date": "2019-02-01T00:00:00Z", "author_hash": "b"}
    rec_a2 = {"id": "repo#1", "author_date": "2019-01-01T00:00:00Z", "author_hash": "a"}
    path.write_text(
        "\n".join(json.dumps(r) for r in (rec_a1, rec_b, rec_a2)) + "\n", encoding="utf-8"
    )
    records = load_candidates(path)
    assert [r["id"] for r in records] == ["repo#1", "repo#2"]


def test_repo_manifest_reports_count_histogram_and_largest_author_share() -> None:
    sampled = [
        {"author_date": "2019-01-01T00:00:00Z", "author_hash": "a"},
        {"author_date": "2019-06-01T00:00:00Z", "author_hash": "a"},
        {"author_date": "2020-01-01T00:00:00Z", "author_hash": "b"},
    ]
    manifest = repo_manifest(sampled)
    assert manifest["count"] == 3
    assert manifest["year_histogram"] == {"2019": 2, "2020": 1}
    assert manifest["largest_author_share"] == 2 / 3


def test_repo_manifest_handles_empty_input() -> None:
    manifest = repo_manifest([])
    assert manifest == {"count": 0, "year_histogram": {}, "largest_author_share": 0.0}


def test_run_writes_sampled_output_and_manifest(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")

    def fake_fetch(*_args: Any, **_kwargs: Any) -> Any:
        yield 1, [RAW_PR_A, RAW_PR_B]

    from collect_prs import run

    out_dir = tmp_path / "prs"
    with patch(FETCH_TARGET, side_effect=fake_fetch):
        exit_code = run(["--repos", "owner/repo", "--out-dir", str(out_dir), "--target", "10"])

    assert exit_code == 0
    output_ids = {
        json.loads(line)["id"] for line in (out_dir / "repo.jsonl").read_text().splitlines()
    }
    assert output_ids == {"repo#1", "repo#2"}
    manifest = json.loads((out_dir / "MANIFEST.json").read_text())
    assert manifest["repo"]["count"] == 2


def test_run_errors_without_github_token(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)

    from collect_prs import run

    exit_code = run(["--out-dir", str(tmp_path / "prs")])
    assert exit_code == 1
