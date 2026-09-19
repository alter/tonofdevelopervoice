# http_retry.py
import http.client
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import TypeVar

T = TypeVar("T")


def is_rate_limited(exc: urllib.error.HTTPError) -> bool:
    return exc.code in (403, 429) and exc.headers.get("x-ratelimit-remaining") == "0"


def rate_limit_wait_seconds(exc: urllib.error.HTTPError) -> float:
    reset_at = exc.headers.get("x-ratelimit-reset")
    if reset_at is None:
        return 60.0
    return max(0.0, float(reset_at) - time.time())


def is_secondary_rate_limited(exc: urllib.error.HTTPError) -> bool:
    if exc.code != 403:
        return False
    if exc.headers.get("retry-after") is not None:
        return True
    try:
        message = json.loads(exc.read()).get("message", "")
    except (OSError, ValueError, AttributeError):
        return False
    return "secondary rate limit" in str(message).lower()


def secondary_rate_limit_wait_seconds(exc: urllib.error.HTTPError) -> float:
    retry_after = exc.headers.get("retry-after")
    if retry_after is None:
        return 60.0
    return float(retry_after)


def fetch_with_retries(
    executor: ThreadPoolExecutor,
    request: urllib.request.Request,
    fetch: Callable[[urllib.request.Request], T],
    sleep: Callable[[float], None] = time.sleep,
    request_timeout: float = 60.0,
    max_transient_attempts: int = 3,
) -> T:
    transient_attempts = 0
    while True:
        try:
            return executor.submit(fetch, request).result(timeout=request_timeout)
        except FutureTimeoutError as exc:
            if transient_attempts < max_transient_attempts:
                transient_attempts += 1
                sleep(2.0**transient_attempts)
                continue
            raise RuntimeError(
                f"GitHub API request timed out after {request_timeout}s"
            ) from exc
        except urllib.error.HTTPError as exc:
            if is_rate_limited(exc):
                sleep(rate_limit_wait_seconds(exc))
                continue
            if is_secondary_rate_limited(exc):
                sleep(secondary_rate_limit_wait_seconds(exc))
                continue
            if 500 <= exc.code < 600 and transient_attempts < max_transient_attempts:
                transient_attempts += 1
                sleep(2.0**transient_attempts)
                continue
            raise RuntimeError(f"GitHub API request failed: {exc.code} {exc.reason}") from exc
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError) as exc:
            if transient_attempts < max_transient_attempts:
                transient_attempts += 1
                sleep(2.0**transient_attempts)
                continue
            raise RuntimeError(f"GitHub API request failed: {exc}") from exc
