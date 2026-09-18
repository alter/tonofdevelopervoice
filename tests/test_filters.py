# test_filters.py
from datetime import UTC, datetime

from tonofdevelopervoice.collect.filters import (
    has_ai_co_author,
    is_before_cutoff,
    is_suspicious_rewrite,
    is_valid_record,
)


def test_has_ai_co_author_detects_claude_trailer() -> None:
    message = "fix memory leak\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
    assert has_ai_co_author(message) is True


def test_has_ai_co_author_detects_case_insensitive_and_other_tools() -> None:
    message = "add retry logic\n\nco-authored-by: GPT-4 <bot@openai.com>"
    assert has_ai_co_author(message) is True


def test_has_ai_co_author_false_for_human_trailer() -> None:
    message = "fix memory leak\n\nCo-authored-by: Jane Doe <jane@example.com>"
    assert has_ai_co_author(message) is False


def test_has_ai_co_author_false_for_plain_message() -> None:
    assert has_ai_co_author("fix off-by-one error in parser") is False


def test_is_before_cutoff_true_for_2020_date() -> None:
    author_date = datetime(2020, 6, 15, tzinfo=UTC)
    assert is_before_cutoff(author_date) is True


def test_is_before_cutoff_false_for_2021_date() -> None:
    author_date = datetime(2021, 1, 1, tzinfo=UTC)
    assert is_before_cutoff(author_date) is False


def test_is_before_cutoff_false_for_2023_date() -> None:
    author_date = datetime(2023, 3, 1, tzinfo=UTC)
    assert is_before_cutoff(author_date) is False


def test_is_suspicious_rewrite_true_for_recent_commit_date() -> None:
    commit_date = datetime(2023, 6, 1, tzinfo=UTC)
    assert is_suspicious_rewrite(commit_date) is True


def test_is_suspicious_rewrite_false_for_period_appropriate_commit_date() -> None:
    commit_date = datetime(2020, 8, 1, tzinfo=UTC)
    assert is_suspicious_rewrite(commit_date) is False


def test_is_valid_record_true_for_genuine_pre2021_commit() -> None:
    author_date = datetime(2019, 3, 1, tzinfo=UTC)
    commit_date = datetime(2019, 5, 1, tzinfo=UTC)
    message = "fix null pointer dereference in handler\n\nSigned-off-by: Jane Doe"
    assert is_valid_record(author_date, commit_date, message) is True


def test_is_valid_record_false_for_post_cutoff_author_date() -> None:
    author_date = datetime(2021, 6, 1, tzinfo=UTC)
    commit_date = datetime(2021, 6, 1, tzinfo=UTC)
    assert is_valid_record(author_date, commit_date, "fix bug") is False


def test_is_valid_record_false_for_ai_co_author() -> None:
    author_date = datetime(2020, 1, 1, tzinfo=UTC)
    commit_date = datetime(2020, 1, 1, tzinfo=UTC)
    message = "fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
    assert is_valid_record(author_date, commit_date, message) is False


def test_is_valid_record_false_for_suspicious_rewrite() -> None:
    author_date = datetime(2020, 1, 1, tzinfo=UTC)
    commit_date = datetime(2023, 9, 1, tzinfo=UTC)
    assert is_valid_record(author_date, commit_date, "fix bug") is False
