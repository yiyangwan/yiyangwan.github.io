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


def test_collect_isolates_malformed_items_and_stops_on_invalid_page_count(window):
    page = json.loads(read_fixture("ticketmaster_page0.json"))
    concert, ballet, *rest = page["_embedded"]["events"]
    malformed = [
        {**concert, "dates": {"start": concert["dates"]["start"], "status": "onsale"}},  # status is a string
        {**ballet, "classifications": ["Music"]},  # classifications are strings
    ]
    body = {"_embedded": {"events": [*malformed, *rest]}, "page": {**page["page"], "totalPages": "x"}}
    http = FakeHttp({CONFIG.url: json.dumps(body)})
    events = ticketmaster.collect(CONFIG, http, window, env=ENV)
    assert [event.uid for event in events] == ["ticketmaster:tm4", "ticketmaster:tm7"]
    assert len(http.calls) == 1


def test_safe_event_isolates_an_overflow_error():
    # An all-day item on datetime.date.max overflows when to_event adds a day for the exclusive end.
    item = {"name": "Overflow Event", "id": "overflow1", "url": "https://example.org/overflow",
           "dates": {"start": {"localDate": "9999-12-31", "noSpecificTime": True}, "status": {"code": "onsale"}},
           "classifications": [{"segment": {"name": "Music"}}],
           "_embedded": {"venues": [{"name": "Test Venue", "city": {"name": "Seattle"}}]}}
    with pytest.raises(OverflowError):
        ticketmaster.to_event(item, CONFIG)
    assert ticketmaster._safe_event(item, CONFIG) is None


def test_page_count_isolates_an_overflow_error():
    assert ticketmaster._page_count(float("inf")) == 0


def test_collect_raises_when_every_item_fails_to_parse(window):
    body = {"_embedded": {"events": [{"name": "No dates"}]}, "page": {"totalPages": 1}}
    http = FakeHttp({CONFIG.url: json.dumps(body)})
    with pytest.raises(SourceError, match="could not parse any items"):
        ticketmaster.collect(CONFIG, http, window, env=ENV)


def test_collect_empty_feed_is_ok(window):
    body = {"_embedded": {"events": []}, "page": {"totalPages": 1}}
    http = FakeHttp({CONFIG.url: json.dumps(body)})
    assert ticketmaster.collect(CONFIG, http, window, env=ENV) == []


def test_non_dict_embedded_raises_unexpected_response(window):
    http = FakeHttp({CONFIG.url: json.dumps({"_embedded": ["oops"], "page": {"totalPages": 1}})})
    with pytest.raises(SourceError, match="unexpected response"):
        ticketmaster.collect(CONFIG, http, window, env=ENV)


def test_non_dict_page_raises_unexpected_response(window):
    http = FakeHttp({CONFIG.url: json.dumps({"_embedded": {"events": []}, "page": ["oops"]})})
    with pytest.raises(SourceError, match="unexpected response"):
        ticketmaster.collect(CONFIG, http, window, env=ENV)
