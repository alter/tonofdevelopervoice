# test_github_search.py
import json
import urllib.error
from email.message import Message
from typing import Any
from unittest.mock import MagicMock, patch

from tonofdevelopervoice.collect.github_search import search

URLOPEN_TARGET = "tonofdevelopervoice.collect.github_search.urllib.request.urlopen"


def _response(items: list[dict[str, Any]]) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(
        {"total_count": len(items), "incomplete_results": False, "items": items}
    ).encode("utf-8")
    return cm


def _fake_urlopen(pages: list[list[dict[str, Any]]]) -> Any:
    remaining = list(pages)

    def _urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        return _response(remaining.pop(0))

    return _urlopen


def test_search_yields_items_across_pages() -> None:
    page1 = [{"id": 1}] * 100
    page2 = [{"id": 2}]
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([page1, page2])):
        items = list(search("commits", "q", "fake-token", sleep=lambda _s: None))
    assert len(items) == 101


def test_search_stops_on_a_short_page() -> None:
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([[{"id": 1}]])):
        items = list(search("commits", "q", "fake-token", per_page=100, sleep=lambda _s: None))
    assert len(items) == 1


def test_search_stops_on_an_empty_page() -> None:
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([[]])):
        items = list(search("commits", "q", "fake-token", sleep=lambda _s: None))
    assert items == []


def test_search_sleeps_between_full_pages_to_respect_the_rate_limit() -> None:
    page1 = [{"id": 1}] * 2
    page2 = [{"id": 2}]
    sleep_calls: list[float] = []
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([page1, page2])):
        list(search("commits", "q", "fake-token", per_page=2, sleep=sleep_calls.append))
    assert sleep_calls == [2.1]


def test_search_stops_at_the_1000_result_cap() -> None:
    pages = [[{"id": i}] * 100 for i in range(20)]
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen(pages)):
        items = list(search("commits", "q", "fake-token", per_page=100, sleep=lambda _s: None))
    assert len(items) == 1000


def test_search_builds_the_expected_url_with_an_encoded_query() -> None:
    with patch(URLOPEN_TARGET, side_effect=_fake_urlopen([[]])) as mock_urlopen:
        list(search("issues", 'type:pr "Generated with"', "fake-token", sleep=lambda _s: None))
    request = mock_urlopen.call_args[0][0]
    assert request.full_url.startswith("https://api.github.com/search/issues?q=")
    assert "type%3Apr" in request.full_url
    assert request.headers["Authorization"] == "Bearer fake-token"


def test_search_delegates_retries_to_http_retry() -> None:
    call_count = 0

    def flaky_urlopen(_request: Any, **_kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            headers = Message()
            headers["x-ratelimit-remaining"] = "0"
            headers["x-ratelimit-reset"] = "1600000000"
            raise urllib.error.HTTPError(
                url="https://api.github.com", code=403, msg="rate limited", hdrs=headers, fp=None
            )
        return _response([{"id": 1}])

    sleep_calls: list[float] = []
    with patch(URLOPEN_TARGET, side_effect=flaky_urlopen):
        items = list(search("commits", "q", "fake-token", sleep=sleep_calls.append))
    assert len(items) == 1
    assert len(sleep_calls) == 1
