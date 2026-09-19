# test_pr_collector.py
import json
import urllib.error
from email.message import Message
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tonofdevelopervoice.collect.github_prs import (
    fetch_pull_requests,
    filter_pull_requests,
    is_valid_pull_request,
    parse_pull_request,
)

URLOPEN_TARGET = "tonofdevelopervoice.collect.github_prs.urllib.request.urlopen"

RAW_PR_VALID = {
    "number": 100,
    "created_at": "2019-05-01T10:00:00Z",
    "merged_at": "2019-05-02T10:00:00Z",
    "user": {"login": "alice", "type": "User"},
    "title": "Fix null pointer dereference",
    "body": "This fixes a null pointer dereference in the request handler.",
}

RAW_PR_UNMERGED = {**RAW_PR_VALID, "number": 101, "merged_at": None}
RAW_PR_BOT = {
    **RAW_PR_VALID,
    "number": 102,
    "user": {"login": "dependabot[bot]", "type": "Bot"},
}
RAW_PR_AI_CO_AUTHOR = {
    **RAW_PR_VALID,
    "number": 103,
    "body": "Fix bug\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
}
RAW_PR_EMPTY_BODY = {**RAW_PR_VALID, "number": 104, "body": "   "}
RAW_PR_TOO_RECENT = {**RAW_PR_VALID, "number": 105, "created_at": "2021-03-01T10:00:00Z"}


def _rate_limited_error() -> urllib.error.HTTPError:
    headers = Message()
    headers["x-ratelimit-remaining"] = "0"
    headers["x-ratelimit-reset"] = "1600000000"
    return urllib.error.HTTPError(
        url="https://api.github.com", code=403, msg="rate limited", hdrs=headers, fp=None
    )


def _server_error(code: int = 502) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.github.com", code=code, msg="Server Error", hdrs=Message(), fp=None
    )


def test_is_valid_pull_request_rejects_unmerged() -> None:
    assert is_valid_pull_request(RAW_PR_UNMERGED) is False


def test_is_valid_pull_request_rejects_bot() -> None:
    assert is_valid_pull_request(RAW_PR_BOT) is False


def test_is_valid_pull_request_rejects_ai_co_author() -> None:
    assert is_valid_pull_request(RAW_PR_AI_CO_AUTHOR) is False


def test_is_valid_pull_request_rejects_empty_body() -> None:
    assert is_valid_pull_request(RAW_PR_EMPTY_BODY) is False


def test_is_valid_pull_request_accepts_a_genuine_pre_2021_pr() -> None:
    assert is_valid_pull_request(RAW_PR_VALID) is True


def test_is_valid_pull_request_rejects_a_pr_created_at_or_after_the_cutoff() -> None:
    assert is_valid_pull_request(RAW_PR_TOO_RECENT) is False


def test_is_valid_pull_request_rejects_a_bot_shaped_login_even_if_typed_user() -> None:
    raw = {**RAW_PR_VALID, "user": {"login": "renovate[bot]", "type": "User"}}
    assert is_valid_pull_request(raw) is False


def test_parse_pull_request_extracts_expected_fields() -> None:
    record = parse_pull_request(RAW_PR_VALID, repo="linux")
    assert record["id"] == "linux#100"
    assert record["source"] == "pr"
    assert record["repo"] == "linux"
    assert record["text"].startswith("Fix null pointer dereference\n\n")
    assert record["author_date"] == "2019-05-01T10:00:00Z"
    assert len(record["author_hash"]) == 12


def test_filter_pull_requests_keeps_only_valid() -> None:
    raw = [RAW_PR_VALID, RAW_PR_UNMERGED, RAW_PR_BOT, RAW_PR_AI_CO_AUTHOR, RAW_PR_EMPTY_BODY]
    kept = list(filter_pull_requests(raw, repo="linux"))
    assert len(kept) == 1
    assert kept[0]["id"] == "linux#100"


def _fake_urlopen(pages: list[list[dict[str, Any]]]) -> Any:
    remaining = list(pages)

    def _urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        body = json.dumps(remaining.pop(0)).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = body
        return cm

    return _urlopen


def test_fetch_pull_requests_stops_at_first_pr_past_cutoff() -> None:
    page = [RAW_PR_VALID, RAW_PR_TOO_RECENT]
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([page])):
        pages = list(
            fetch_pull_requests(
                "owner/repo", "fake-token", "2021-01-01T00:00:00Z", per_page=100
            )
        )
    assert len(pages) == 1
    page_number, kept = pages[0]
    assert page_number == 1
    assert len(kept) == 1
    assert kept[0]["number"] == 100


def test_fetch_pull_requests_paginates_until_short_page() -> None:
    page1 = [RAW_PR_VALID] * 2
    page2 = [RAW_PR_VALID]
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([page1, page2])):
        pages = list(
            fetch_pull_requests("owner/repo", "fake-token", "2021-01-01T00:00:00Z", per_page=2)
        )
    assert [p for p, _ in pages] == [1, 2]
    assert sum(len(kept) for _, kept in pages) == 3


def test_fetch_pull_requests_stops_on_empty_page() -> None:
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([[]])):
        pages = list(fetch_pull_requests("owner/repo", "fake-token", "2021-01-01T00:00:00Z"))
    assert pages == []


def test_fetch_pull_requests_sleeps_and_retries_after_rate_limit() -> None:
    call_count = 0

    def flaky_urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _rate_limited_error()
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = json.dumps([RAW_PR_VALID]).encode("utf-8")
        return cm

    sleep_calls: list[float] = []
    with patch(URLOPEN_TARGET, side_effect=flaky_urlopen):
        pages = list(
            fetch_pull_requests(
                "owner/repo",
                "fake-token",
                "2021-01-01T00:00:00Z",
                sleep=sleep_calls.append,
            )
        )
    assert len(sleep_calls) == 1
    assert sleep_calls[0] >= 0
    assert len(pages) == 1


def test_fetch_pull_requests_retries_on_server_error_then_succeeds() -> None:
    call_count = 0

    def flaky_urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise _server_error()
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = json.dumps([RAW_PR_VALID]).encode("utf-8")
        return cm

    sleep_calls: list[float] = []
    with patch(URLOPEN_TARGET, side_effect=flaky_urlopen):
        pages = list(
            fetch_pull_requests(
                "owner/repo",
                "fake-token",
                "2021-01-01T00:00:00Z",
                sleep=sleep_calls.append,
            )
        )
    assert len(sleep_calls) == 2
    assert len(pages) == 1


def test_fetch_pull_requests_sleeps_a_default_minute_when_reset_header_is_missing() -> None:
    call_count = 0

    def flaky_urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            headers = Message()
            headers["x-ratelimit-remaining"] = "0"
            raise urllib.error.HTTPError(
                url="https://api.github.com", code=403, msg="rate limited", hdrs=headers, fp=None
            )
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = json.dumps([RAW_PR_VALID]).encode("utf-8")
        return cm

    sleep_calls: list[float] = []
    with patch(URLOPEN_TARGET, side_effect=flaky_urlopen):
        list(
            fetch_pull_requests(
                "owner/repo",
                "fake-token",
                "2021-01-01T00:00:00Z",
                sleep=sleep_calls.append,
            )
        )
    assert sleep_calls == [60.0]


def test_fetch_pull_requests_passes_a_request_timeout_so_a_stall_cannot_hang_forever() -> None:
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([[RAW_PR_VALID]])) as mock_urlopen:
        list(fetch_pull_requests("owner/repo", "fake-token", "2021-01-01T00:00:00Z"))
    _request, kwargs = mock_urlopen.call_args
    assert kwargs.get("timeout") is not None
    assert kwargs["timeout"] > 0


def test_fetch_pull_requests_gives_up_waiting_on_a_dribbling_response_and_retries() -> None:
    import threading

    call_count = 0
    release = threading.Event()

    def slow_then_fast_urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        cm = MagicMock()
        if call_count == 1:
            release.wait(30)
            cm.__enter__.return_value.read.return_value = json.dumps([]).encode("utf-8")
        else:
            cm.__enter__.return_value.read.return_value = json.dumps([RAW_PR_VALID]).encode(
                "utf-8"
            )
        return cm

    sleep_calls: list[float] = []
    try:
        with patch(URLOPEN_TARGET, side_effect=slow_then_fast_urlopen):
            pages = list(
                fetch_pull_requests(
                    "owner/repo",
                    "fake-token",
                    "2021-01-01T00:00:00Z",
                    sleep=sleep_calls.append,
                    request_timeout=0.05,
                )
            )
    finally:
        release.set()
    assert len(sleep_calls) == 1
    assert len(pages) == 1


def test_fetch_pull_requests_retries_after_a_socket_timeout_then_succeeds() -> None:
    call_count = 0

    def flaky_urlopen(_request: Any, timeout: float | None = None) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("timed out")
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = json.dumps([RAW_PR_VALID]).encode("utf-8")
        return cm

    sleep_calls: list[float] = []
    with patch(URLOPEN_TARGET, side_effect=flaky_urlopen):
        pages = list(
            fetch_pull_requests(
                "owner/repo",
                "fake-token",
                "2021-01-01T00:00:00Z",
                sleep=sleep_calls.append,
            )
        )
    assert len(sleep_calls) == 1
    assert len(pages) == 1


def test_fetch_pull_requests_retries_after_a_truncated_read_then_succeeds() -> None:
    import http.client

    call_count = 0

    def flaky_urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        cm = MagicMock()
        if call_count == 1:
            cm.__enter__.return_value.read.side_effect = http.client.IncompleteRead(
                b"partial", 25700
            )
        else:
            cm.__enter__.return_value.read.return_value = json.dumps(
                [RAW_PR_VALID]
            ).encode("utf-8")
        return cm

    sleep_calls: list[float] = []
    with patch(URLOPEN_TARGET, side_effect=flaky_urlopen):
        pages = list(
            fetch_pull_requests(
                "owner/repo",
                "fake-token",
                "2021-01-01T00:00:00Z",
                sleep=sleep_calls.append,
            )
        )
    assert len(sleep_calls) == 1
    assert len(pages) == 1


def test_fetch_pull_requests_raises_after_repeated_truncated_reads() -> None:
    import http.client

    def always_truncated(_request: Any, **_kwargs: Any) -> MagicMock:
        cm = MagicMock()
        cm.__enter__.return_value.read.side_effect = http.client.IncompleteRead(b"x", 1)
        return cm

    with (
        patch(URLOPEN_TARGET, side_effect=always_truncated),
        pytest.raises(RuntimeError, match="IncompleteRead"),
    ):
        list(
            fetch_pull_requests(
                "owner/repo", "fake-token", "2021-01-01T00:00:00Z", sleep=lambda _s: None
            )
        )


def test_fetch_pull_requests_raises_after_repeated_stalls() -> None:
    import time as time_module

    def always_stalls(_request: Any, **_kwargs: Any) -> MagicMock:
        time_module.sleep(1)
        return MagicMock()

    with (
        patch(URLOPEN_TARGET, side_effect=always_stalls),
        pytest.raises(RuntimeError, match="timed out"),
    ):
        list(
            fetch_pull_requests(
                "owner/repo",
                "fake-token",
                "2021-01-01T00:00:00Z",
                sleep=lambda _s: None,
                request_timeout=0.01,
            )
        )


def test_fetch_pull_requests_raises_after_repeated_server_errors() -> None:
    def always_fail(_request: Any, **_kwargs: Any) -> MagicMock:
        raise _server_error()

    with (
        patch(URLOPEN_TARGET, side_effect=always_fail),
        pytest.raises(RuntimeError, match="502"),
    ):
        list(
            fetch_pull_requests(
                "owner/repo", "fake-token", "2021-01-01T00:00:00Z", sleep=lambda _s: None
            )
        )
