# test_http_retry.py
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
from typing import Any

import pytest

from tonofdevelopervoice.collect.http_retry import (
    fetch_with_retries,
    is_rate_limited,
    rate_limit_wait_seconds,
)

REQUEST = urllib.request.Request("https://api.github.com/example")


def _http_error(code: int, headers: Message | None = None) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://api.github.com", code=code, msg="error", hdrs=headers or Message(), fp=None
    )


def _rate_limited_headers(reset_at: str | None = "1600000000") -> Message:
    headers = Message()
    headers["x-ratelimit-remaining"] = "0"
    if reset_at is not None:
        headers["x-ratelimit-reset"] = reset_at
    return headers


def test_is_rate_limited_true_only_when_remaining_is_zero() -> None:
    assert is_rate_limited(_http_error(403, _rate_limited_headers())) is True
    assert is_rate_limited(_http_error(403, Message())) is False
    assert is_rate_limited(_http_error(404, _rate_limited_headers())) is False


def test_rate_limit_wait_seconds_defaults_to_a_minute_without_a_reset_header() -> None:
    assert rate_limit_wait_seconds(_http_error(403, Message())) == 60.0


def test_rate_limit_wait_seconds_uses_the_reset_header() -> None:
    now = time.time()
    exc = _http_error(403, _rate_limited_headers(str(now + 30)))
    assert 25 <= rate_limit_wait_seconds(exc) <= 30


def test_fetch_with_retries_returns_the_first_successful_result() -> None:
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = fetch_with_retries(executor, REQUEST, fetch=lambda _r: "ok")
    assert result == "ok"


def test_fetch_with_retries_sleeps_and_retries_after_rate_limit() -> None:
    call_count = 0

    def flaky(_request: Any) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise _http_error(403, _rate_limited_headers())
        return "ok"

    sleep_calls: list[float] = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = fetch_with_retries(executor, REQUEST, fetch=flaky, sleep=sleep_calls.append)
    assert result == "ok"
    assert len(sleep_calls) == 1


def test_fetch_with_retries_retries_on_5xx_then_succeeds() -> None:
    call_count = 0

    def flaky(_request: Any) -> str:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise _http_error(502)
        return "ok"

    sleep_calls: list[float] = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = fetch_with_retries(executor, REQUEST, fetch=flaky, sleep=sleep_calls.append)
    assert result == "ok"
    assert len(sleep_calls) == 2


def test_fetch_with_retries_raises_after_repeated_5xx() -> None:
    def always_fails(_request: Any) -> str:
        raise _http_error(502)

    with ThreadPoolExecutor(max_workers=2) as executor, pytest.raises(RuntimeError, match="502"):
        fetch_with_retries(executor, REQUEST, fetch=always_fails, sleep=lambda _s: None)


def test_fetch_with_retries_does_not_retry_a_non_retryable_http_error() -> None:
    call_count = 0

    def not_found(_request: Any) -> str:
        nonlocal call_count
        call_count += 1
        raise _http_error(404)

    with ThreadPoolExecutor(max_workers=2) as executor, pytest.raises(RuntimeError, match="404"):
        fetch_with_retries(executor, REQUEST, fetch=not_found, sleep=lambda _s: None)
    assert call_count == 1


def test_fetch_with_retries_retries_a_connection_level_error_then_succeeds() -> None:
    import http.client

    call_count = 0

    def flaky(_request: Any) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise http.client.IncompleteRead(b"partial", 10)
        return "ok"

    sleep_calls: list[float] = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = fetch_with_retries(executor, REQUEST, fetch=flaky, sleep=sleep_calls.append)
    assert result == "ok"
    assert len(sleep_calls) == 1


def test_fetch_with_retries_raises_after_repeated_connection_level_errors() -> None:
    import http.client

    def always_truncated(_request: Any) -> str:
        raise http.client.IncompleteRead(b"x", 1)

    with (
        ThreadPoolExecutor(max_workers=2) as executor,
        pytest.raises(RuntimeError, match="IncompleteRead"),
    ):
        fetch_with_retries(executor, REQUEST, fetch=always_truncated, sleep=lambda _s: None)


def test_fetch_with_retries_gives_up_on_a_dribbling_response_and_retries() -> None:
    call_count = 0

    def slow_then_fast(_request: Any) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            time.sleep(1)
        return "ok"

    sleep_calls: list[float] = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        result = fetch_with_retries(
            executor,
            REQUEST,
            fetch=slow_then_fast,
            sleep=sleep_calls.append,
            request_timeout=0.01,
        )
    assert result == "ok"
    assert len(sleep_calls) == 1


def test_fetch_with_retries_raises_after_repeated_stalls() -> None:
    def always_stalls(_request: Any) -> str:
        time.sleep(1)
        return "unreachable"

    with (
        ThreadPoolExecutor(max_workers=2) as executor,
        pytest.raises(RuntimeError, match="timed out"),
    ):
        fetch_with_retries(
            executor,
            REQUEST,
            fetch=always_stalls,
            sleep=lambda _s: None,
            request_timeout=0.01,
        )
