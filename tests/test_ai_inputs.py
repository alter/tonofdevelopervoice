# test_ai_inputs.py
from datetime import datetime

from tonofdevelopervoice.evaluate.ai_inputs import (
    COMMIT_MIN_LENGTH,
    PR_MIN_LENGTH,
    detect_agent,
    extract_generated_with_agent,
    is_eligible,
    parse_ai_commit,
    parse_ai_pr,
    select_ai_commits,
    select_ai_prs,
    select_with_repo_cap,
    strip_ai_markers,
)

AI_COMMIT_MESSAGE = (
    "Improve caching layer for request handler\n\n"
    "This change adds a small in-memory cache in front of the expensive lookup "
    "path, invalidated on write, and adds a metric for the hit rate so we can "
    "see whether it is actually helping in production before expanding it "
    "further. Also documented the new behaviour in the module docstring so the "
    "next reader does not have to guess.\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>"
)

AI_PR_BODY = (
    "## Summary\n\n"
    "This pull request fixes a race condition in the connection pool where two "
    "callers could both believe they had acquired the last available slot, "
    "leading to a transient over-allocation under load. Added a regression test "
    "that reproduces the race deterministically and verified it fails on the "
    "old code before the fix and passes after. Also updated the pool's "
    "docstring to describe the invariant being protected here in some detail "
    "so a future change does not reintroduce the same bug by accident.\n\n"
    "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
)

RAW_AI_COMMIT = {
    "sha": "abc123",
    "commit": {
        "author": {"date": "2023-06-01T10:00:00Z"},
        "message": AI_COMMIT_MESSAGE,
    },
    "repository": {"full_name": "octo/widgets"},
}

RAW_HUMAN_COMMIT_PRE_2021 = {
    "sha": "def456",
    "commit": {
        "author": {"date": "2019-06-01T10:00:00Z"},
        "message": "fix null pointer dereference in handler",
    },
    "repository": {"full_name": "octo/widgets"},
}

RAW_AI_PR = {
    "number": 42,
    "created_at": "2023-07-01T10:00:00Z",
    "body": AI_PR_BODY,
    "repository_url": "https://api.github.com/repos/octo/widgets",
}


def test_extract_generated_with_agent_reads_the_bracketed_form() -> None:
    assert (
        extract_generated_with_agent("🤖 Generated with [Claude Code](https://x)")
        == "Claude Code"
    )


def test_extract_generated_with_agent_reads_the_plain_form() -> None:
    assert extract_generated_with_agent("Generated with Cursor") == "Cursor"


def test_extract_generated_with_agent_returns_none_when_absent() -> None:
    assert extract_generated_with_agent("just a normal commit message") is None


def test_detect_agent_prefers_the_co_authored_by_trailer() -> None:
    assert detect_agent(AI_COMMIT_MESSAGE) == "Claude"


def test_detect_agent_falls_back_to_generated_with_marker() -> None:
    assert detect_agent(AI_PR_BODY) == "Claude Code"


def test_detect_agent_returns_none_for_human_text() -> None:
    assert detect_agent("fix null pointer dereference in handler") is None


def test_strip_ai_markers_removes_the_trailer_and_the_generated_with_line() -> None:
    stripped = strip_ai_markers(AI_COMMIT_MESSAGE)
    assert "Co-Authored-By" not in stripped
    assert "Improve caching layer" in stripped

    stripped_pr = strip_ai_markers(AI_PR_BODY)
    assert "Generated with" not in stripped_pr
    assert "race condition" in stripped_pr


def test_is_eligible_rejects_a_pre_2021_human_commit() -> None:
    assert (
        is_eligible(
            "fix null pointer dereference in handler",
            datetime.fromisoformat("2019-06-01T10:00:00+00:00"),
            COMMIT_MIN_LENGTH,
        )
        is False
    )


def test_is_eligible_rejects_otherwise_eligible_ai_text_dated_before_the_cutoff() -> None:
    assert (
        is_eligible(
            AI_COMMIT_MESSAGE,
            datetime.fromisoformat("2019-06-01T10:00:00+00:00"),
            COMMIT_MIN_LENGTH,
        )
        is False
    )


def test_is_eligible_rejects_text_that_is_too_short() -> None:
    assert (
        is_eligible(
            "Co-Authored-By: Claude <noreply@anthropic.com>",
            datetime.fromisoformat("2023-06-01T10:00:00+00:00"),
            COMMIT_MIN_LENGTH,
        )
        is False
    )


def test_is_eligible_accepts_a_genuine_ai_commit() -> None:
    assert (
        is_eligible(
            AI_COMMIT_MESSAGE,
            datetime.fromisoformat("2023-06-01T10:00:00+00:00"),
            COMMIT_MIN_LENGTH,
        )
        is True
    )


def test_parse_ai_commit_extracts_expected_fields() -> None:
    record = parse_ai_commit(RAW_AI_COMMIT)
    assert record["id"] == "abc123"
    assert record["source"] == "ai_commit"
    assert record["repo"] == "octo/widgets"
    assert record["date"] == "2023-06-01T10:00:00Z"
    assert record["agent"] == "Claude"
    assert "Co-Authored-By" not in record["text"]


def test_parse_ai_pr_extracts_expected_fields() -> None:
    record = parse_ai_pr(RAW_AI_PR)
    assert record["id"] == "octo/widgets#42"
    assert record["source"] == "ai_pr"
    assert record["repo"] == "octo/widgets"
    assert record["agent"] == "Claude Code"
    assert "Generated with" not in record["text"]


def test_select_ai_commits_keeps_only_eligible_ones() -> None:
    selected = list(select_ai_commits([RAW_AI_COMMIT, RAW_HUMAN_COMMIT_PRE_2021]))
    assert [r["id"] for r in selected] == ["abc123"]


def test_select_ai_prs_keeps_only_eligible_ones() -> None:
    ineligible = {**RAW_AI_PR, "number": 43, "body": "too short"}
    selected = list(select_ai_prs([RAW_AI_PR, ineligible]))
    assert [r["id"] for r in selected] == ["octo/widgets#42"]
    assert selected[0]["text"].startswith("## Summary")
    assert PR_MIN_LENGTH > 0


def test_select_with_repo_cap_enforces_the_cap() -> None:
    items = [{"repo": "a", "text": f"item {i}"} for i in range(10)]
    selected = select_with_repo_cap(items, cap=5)
    assert len(selected) == 5


def test_select_with_repo_cap_drops_exact_duplicate_text() -> None:
    items = [
        {"repo": "a", "text": "same text"},
        {"repo": "b", "text": "same text"},
        {"repo": "a", "text": "different text"},
    ]
    selected = select_with_repo_cap(items, cap=5)
    assert len(selected) == 2
