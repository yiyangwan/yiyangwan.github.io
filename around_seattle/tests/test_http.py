import itertools

import pytest
import requests

from around_seattle.http import USER_AGENT, FetchError, HttpClient

FEED = "https://feeds.example.org/events.ics"
ROBOTS = "https://feeds.example.org/robots.txt"


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, routes):
        self.headers = {}
        self.routes = {url: list(items) if isinstance(items, list) else [items] for url, items in routes.items()}
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(url)
        queue = self.routes[url]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item


def make_client(routes, clock=None):
    sleeps = []
    session = FakeSession(routes)
    client = HttpClient(session=session, sleep=sleeps.append, clock=clock or (lambda: 100.0))
    return client, session, sleeps


def test_sets_user_agent():
    _, session, _ = make_client({})
    assert session.headers["User-Agent"] == USER_AGENT


def test_returns_body_when_robots_allows():
    client, session, _ = make_client({ROBOTS: FakeResponse(200, "User-agent: *\nDisallow:\n"),
                                      FEED: FakeResponse(200, "hello")})
    assert client.get_text(FEED) == "hello"
    assert session.calls == [ROBOTS, FEED]


def test_robots_disallow_blocks_the_request():
    client, session, _ = make_client({ROBOTS: FakeResponse(200, "User-agent: *\nDisallow: /events.ics\n"),
                                      FEED: FakeResponse(200, "x")})
    with pytest.raises(FetchError, match="robots.txt disallows"):
        client.get_text(FEED)
    assert FEED not in session.calls


def test_robots_404_means_no_restrictions():
    client, _, _ = make_client({ROBOTS: FakeResponse(404), FEED: FakeResponse(200, "x")})
    assert client.get_text(FEED) == "x"


def test_robots_unreachable_means_disallow():
    client, _, _ = make_client({ROBOTS: requests.ConnectionError("down"), FEED: FakeResponse(200, "x")})
    with pytest.raises(FetchError, match="robots.txt disallows"):
        client.get_text(FEED)


def test_robots_is_fetched_once_per_host():
    client, session, _ = make_client({ROBOTS: FakeResponse(404), FEED: FakeResponse(200, "x")})
    client.get_text(FEED)
    client.get_text(FEED)
    assert session.calls.count(ROBOTS) == 1


def test_respect_robots_false_skips_robots():
    client, session, _ = make_client({FEED: FakeResponse(200, "x")})
    assert client.get_text(FEED, respect_robots=False) == "x"
    assert ROBOTS not in session.calls


def test_retries_once_on_server_error():
    client, _, sleeps = make_client({FEED: [FakeResponse(503), FakeResponse(200, "ok")]})
    assert client.get_text(FEED, respect_robots=False) == "ok"
    assert sleeps == [2.0]


def test_second_server_error_raises_status():
    client, _, _ = make_client({FEED: [FakeResponse(503), FakeResponse(502)]})
    with pytest.raises(FetchError, match="^HTTP 502$"):
        client.get_text(FEED, respect_robots=False)


def test_client_error_raises_without_retry():
    client, session, _ = make_client({FEED: FakeResponse(403)})
    with pytest.raises(FetchError, match="^HTTP 403$"):
        client.get_text(FEED, respect_robots=False)
    assert session.calls == [FEED]


def test_network_errors_raise_class_name_without_url():
    boom = requests.ConnectionError(f"Max retries exceeded with url: {FEED}?apikey=SECRET")
    client, _, _ = make_client({FEED: [boom, boom]})
    with pytest.raises(FetchError) as info:
        client.get_text(FEED, respect_robots=False)
    assert str(info.value) == "ConnectionError"
    assert "SECRET" not in str(info.value)


def test_get_json_parses_and_rejects_html():
    client, _, _ = make_client({FEED: [FakeResponse(200, '{"a": 1}'), FakeResponse(200, "<html>")]})
    assert client.get_json(FEED, respect_robots=False) == {"a": 1}
    with pytest.raises(FetchError, match="invalid JSON"):
        client.get_json(FEED, respect_robots=False)


def test_min_interval_paces_requests_to_the_same_host():
    clock = itertools.chain([100.0, 103.0], itertools.repeat(110.0))
    client, _, sleeps = make_client({FEED: FakeResponse(200, "x")}, clock=lambda: next(clock))
    client.get_text(FEED, respect_robots=False, min_interval=10)
    client.get_text(FEED, respect_robots=False, min_interval=10)
    assert sleeps == [7.0]
