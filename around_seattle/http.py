"""HTTP access for the pipeline: one session, polite pacing, robots.txt, short errors."""
from __future__ import annotations

import json
import time
from urllib import robotparser
from urllib.parse import urlsplit

import requests

from .models import SourceError

USER_AGENT = "AroundSeattle/1.0 (+https://yiyangwan.github.io/around-seattle/)"
ROBOTS_AGENT = "AroundSeattle"
RETRY_DELAY_SECONDS = 2.0


class FetchError(SourceError):
    """A request failed; the message is short and safe to publish (for example, 'HTTP 403')."""


class _Robots:
    """robots.txt rules for one host. Fetch failures follow RFC 9309 section 2.3.1."""

    def __init__(self, parser: robotparser.RobotFileParser | None, allow_all: bool) -> None:
        self._parser = parser
        self._allow_all = allow_all

    def allows(self, url: str) -> bool:
        if self._parser is None:
            return self._allow_all
        return self._parser.can_fetch(ROBOTS_AGENT, url)


class HttpClient:
    def __init__(self, session=None, timeout: float = 20.0, sleep=time.sleep, clock=time.monotonic) -> None:
        self._session = session if session is not None else requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._timeout = timeout
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, _Robots] = {}

    def get_text(self, url, params=None, *, min_interval=0.0, respect_robots=True, headers=None) -> str:
        return self._get(url, params, min_interval, respect_robots, headers).text

    def get_json(self, url, params=None, *, min_interval=0.0, respect_robots=True, headers=None):
        response = self._get(url, params, min_interval, respect_robots, headers)
        try:
            return json.loads(response.text)
        except ValueError as exc:
            raise FetchError("invalid JSON") from exc

    def _get(self, url, params, min_interval, respect_robots, headers):
        host = urlsplit(url).netloc
        if respect_robots and not self._robots_for(url).allows(url):
            raise FetchError("robots.txt disallows")
        for attempt in (1, 2):
            self._pace(host, min_interval)
            try:
                response = self._session.get(url, params=params, headers=headers, timeout=self._timeout)
            except requests.RequestException as exc:
                self._last_request[host] = self._clock()
                if attempt == 2:
                    # Only the class name: requests' messages include the URL, and a query string can hold a key.
                    raise FetchError(type(exc).__name__) from None
                self._sleep(RETRY_DELAY_SECONDS)
                continue
            self._last_request[host] = self._clock()
            if response.status_code >= 500 and attempt == 1:
                self._sleep(RETRY_DELAY_SECONDS)
                continue
            if response.status_code != 200:
                raise FetchError(f"HTTP {response.status_code}")
            return response
        raise FetchError("request failed")

    def _pace(self, host, min_interval):
        last = self._last_request.get(host)
        if last is None or min_interval <= 0:
            return
        wait = min_interval - (self._clock() - last)
        if wait > 0:
            self._sleep(wait)

    def _robots_for(self, url) -> _Robots:
        parts = urlsplit(url)
        if parts.netloc not in self._robots:
            self._robots[parts.netloc] = self._load_robots(f"{parts.scheme}://{parts.netloc}/robots.txt")
        return self._robots[parts.netloc]

    def _load_robots(self, robots_url) -> _Robots:
        try:
            response = self._session.get(robots_url, timeout=self._timeout)
        except requests.RequestException:
            return _Robots(None, allow_all=False)  # unreachable: assume complete disallow
        if 400 <= response.status_code < 500:
            return _Robots(None, allow_all=True)  # unavailable: no restrictions
        if response.status_code != 200:
            return _Robots(None, allow_all=False)
        parser = robotparser.RobotFileParser()
        parser.parse(response.text.splitlines())
        return _Robots(parser, allow_all=True)
