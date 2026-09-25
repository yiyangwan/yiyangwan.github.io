import json
from datetime import datetime

import pytest

from around_seattle.models import LA, SourceError, SourceSkipped
from around_seattle.sources import ticketmaster
from around_seattle.tests.conftest import FakeHttp, make_config, read_fixture

CONFIG = make_config(id="ticketmaster", type="ticketmaster", region=None, respect_robots=False,
                     url="https://app.ticketmaster.com/discovery/v2/events.json",
                     secret_env="TICKETMASTER_API_KEY", max_pages=5, min_interval_seconds=0.25)
ENV = {"TICKETMASTER_API_KEY": "test-key"}


def test_dormant_without_key(window):
    http = FakeHttp({})
    with pytest.raises(SourceSkipped):
        ticketmaster.collect(CONFIG, http, window, env={})
    assert http.calls == []


def test_query_parameters(window):
    http = FakeHttp({CONFIG.url: read_fixture("ticketmaster_page0.json")})
    ticketmaster.collect(CONFIG, http, window, env=ENV)
    url, params, kwargs = http.calls[0]
    assert params == {"apikey": "test-key", "dmaId": 385, "size": 200, "page": 0, "sort": "date,asc",
                      "startDateTime": "2026-09-25T07:00:00Z", "endDateTime": "2026-11-25T08:00:00Z"}
    assert kwargs == {"min_interval": 0.25, "respect_robots": False}


def test_keeps_music_and_arts_and_drops_add_ons_sports_and_cancellations(window):
    http = FakeHttp({CONFIG.url: read_fixture("ticketmaster_page0.json")})
    events = ticketmaster.collect(CONFIG, http, window, env=ENV)
    assert [event.uid for event in events] == ["ticketmaster:tm1", "ticketmaster:tm2", "ticketmaster:tm4",
                                               "ticketmaster:tm7"]


def test_event_fields():
    items = json.loads(read_fixture("ticketmaster_page0.json"))["_embedded"]["events"]
    concert = ticketmaster.to_event(items[0], CONFIG)
    assert concert.start == datetime(2026, 10, 2, 19, 30, tzinfo=LA)
    assert concert.venue == "Climate Pledge Arena"
    assert concert.city == "Seattle"
    assert concert.location_text == "Climate Pledge Arena, 334 1st Ave N, Seattle, WA"
    assert concert.price == "$45 to $95"
    assert concert.raw_categories == ("Music", "Rock", "Indie Rock")
    ballet = ticketmaster.to_event(items[1], CONFIG)
    assert ballet.price == "$30"
    assert ballet.raw_categories == ("Arts & Theatre", "Dance")
    jazz = ticketmaster.to_event(items[6], CONFIG)
    assert jazz.all_day is True
    assert jazz.end == datetime(2026, 10, 11, 0, 0, tzinfo=LA)


def test_paginates_until_total_pages(window):
    page = json.loads(read_fixture("ticketmaster_page0.json"))
    page["page"]["totalPages"] = 2
    http = FakeHttp({CONFIG.url: json.dumps(page)})
    ticketmaster.collect(CONFIG, http, window, env=ENV)
    assert [call[1]["page"] for call in http.calls] == [0, 1]


def test_unexpected_response_raises(window):
    http = FakeHttp({CONFIG.url: "[]"})
    with pytest.raises(SourceError, match="unexpected response"):
        ticketmaster.collect(CONFIG, http, window, env=ENV)
