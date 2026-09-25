import json
from datetime import datetime
from pathlib import Path

import pytest

from around_seattle.http import FetchError
from around_seattle.models import LA, Event, SourceConfig, Window

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 25, 6, 0, tzinfo=LA)  # a Friday morning


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def make_config(**overrides) -> SourceConfig:
    base = dict(id="test", name="Test Source", homepage="https://example.org/", type="ics",
                url="https://example.org/feed", region="seattle", weight=20)
    base.update(overrides)
    return SourceConfig(**base)


def make_event(**overrides) -> Event:
    base = dict(source_id="test", uid="u1", title="Community Festival",
                start=datetime(2026, 9, 26, 11, 0, tzinfo=LA), end=datetime(2026, 9, 26, 16, 0, tzinfo=LA),
                all_day=False)
    base.update(overrides)
    return Event(**base)


class FakeHttp:
    """Maps URL to text, or to a callable(params) returning text; unknown URLs raise FetchError."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get_text(self, url, params=None, **kwargs):
        self.calls.append((url, dict(params or {}), kwargs))
        handler = self.routes.get(url)
        if handler is None:
            raise FetchError("HTTP 404")
        value = handler(dict(params or {})) if callable(handler) else handler
        if isinstance(value, Exception):
            raise value
        return value

    def get_json(self, url, params=None, **kwargs):
        return json.loads(self.get_text(url, params, **kwargs))


@pytest.fixture
def window() -> Window:
    return Window.starting(NOW)
