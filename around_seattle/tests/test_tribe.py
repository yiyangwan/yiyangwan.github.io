import json
from datetime import datetime

import pytest

from around_seattle.models import LA, SourceError
from around_seattle.sources import tribe
from around_seattle.tests.conftest import FakeHttp, make_config, read_fixture

CONFIG = make_config(id="town-hall", type="tribe", url="https://townhallseattle.org/wp-json/tribe/events/v1/events",
                     min_interval_seconds=10.0)


def pages(params):
    return read_fixture("tribe_page1.json" if params["page"] == 1 else "tribe_page2.json")


def items(name):
    return json.loads(read_fixture(name))["events"]


def test_collect_paginates_with_window_dates(window):
    http = FakeHttp({CONFIG.url: pages})
    events = tribe.collect(CONFIG, http, window)
    assert [event.uid for event in events] == ["town-hall:501", "town-hall:502", "town-hall:505"]
    assert [call[1]["page"] for call in http.calls] == [1, 2]
    assert http.calls[0][1] == {"start_date": "2026-09-25", "end_date": "2026-11-24", "per_page": 50, "page": 1}
    assert http.calls[0][2] == {"min_interval": 10.0, "respect_robots": True}


def test_collect_stops_at_max_pages(window):
    http = FakeHttp({CONFIG.url: pages})
    tribe.collect(make_config(id="town-hall", type="tribe", url=CONFIG.url, max_pages=1), http, window)
    assert len(http.calls) == 1


def test_timed_event_fields():
    event = tribe.to_event(items("tribe_page1.json")[0], CONFIG)
    assert event.title == "Global Rhythms: Ganesh Rajagopalan with Marina Albero"
    assert event.start == datetime(2026, 9, 25, 19, 30, tzinfo=LA)
    assert event.end is None
    assert event.venue == "The Forum"
    assert event.city == "Seattle"
    assert event.location_text == "The Forum, 1119 8th Ave, Seattle, WA"
    assert (event.price, event.free) == ("$10 – $35 Sliding Scale", False)
    assert event.raw_categories == ("Arts & Culture",)
    assert event.summary == "An evening of Carnatic violin and piano. Questions:"


def test_all_day_event_spans_to_midnight_after_last_day():
    event = tribe.to_event(items("tribe_page1.json")[1], CONFIG)
    assert event.title == "Fall Harvest Festival at Remlinger’s"
    assert event.all_day is True
    assert event.start == datetime(2026, 10, 3, 0, 0, tzinfo=LA)
    assert event.end == datetime(2026, 10, 5, 0, 0, tzinfo=LA)
    assert event.city == "Carnation"
    assert event.free is True


def test_skips_virtual_hidden_and_malformed_items():
    data = items("tribe_page2.json")
    assert tribe.to_event(data[0], CONFIG) is None  # virtual with no venue
    assert tribe.to_event(data[1], CONFIG) is None  # hidden from listings
    assert tribe.to_event({"title": "No date"}, CONFIG) is None
    assert tribe.to_event("not a dict", CONFIG) is None
    no_venue = tribe.to_event(data[2], CONFIG)
    assert no_venue.venue is None
    assert no_venue.summary == "An intimate duo set."


def test_summary_strips_markup_runs():
    item = {"id": 999, "status": "publish", "hide_from_listings": False, "is_virtual": False,
           "title": "Trivia Night", "start_date": "2026-09-26 19:00:00", "timezone": "America/Los_Angeles",
           "all_day": False, "excerpt": "** 6:00 p.m. ** doors"}
    event = tribe.to_event(item, CONFIG)
    assert event.summary == "6:00 p.m. doors"


def test_unexpected_response_raises(window):
    http = FakeHttp({CONFIG.url: '{"code": "rest_no_route"}'})
    with pytest.raises(SourceError, match="unexpected response"):
        tribe.collect(CONFIG, http, window)


def test_collect_isolates_malformed_items_and_stops_on_invalid_page_count(window):
    bad_zone = {"title": "Bad", "start_date": "2026-09-26 10:00:00", "timezone": 5}
    # A non-string time zone falls back to Los Angeles instead of raising.
    assert tribe.to_event(bad_zone, CONFIG).start == datetime(2026, 9, 26, 10, 0, tzinfo=LA)
    # A non-list "categories" still raises inside to_event, so collect skips that item alone.
    # A valid item before AND after the malformed one must both survive.
    page = {"events": [items("tribe_page1.json")[0], {**bad_zone, "categories": 5}, items("tribe_page1.json")[1]],
           "total_pages": "n/a"}
    http = FakeHttp({CONFIG.url: json.dumps(page)})
    assert [event.uid for event in tribe.collect(CONFIG, http, window)] == ["town-hall:501", "town-hall:502"]
    assert len(http.calls) == 1


def test_zone_falls_back_when_name_is_a_directory():
    # ZoneInfo("America") raises IsADirectoryError (an OSError), not one of the other caught types.
    assert tribe._zone("America") is LA


def test_safe_event_isolates_an_overflow_error():
    # An all-day item whose last day is already datetime.date.max overflows when to_event adds a
    # day to compute the exclusive end.
    item = {"id": 999, "status": "publish", "hide_from_listings": False, "is_virtual": False,
           "title": "Overflow Event", "start_date": "9999-12-31 00:00:00", "all_day": True}
    with pytest.raises(OverflowError):
        tribe.to_event(item, CONFIG)
    assert tribe._safe_event(item, CONFIG) is None


def test_page_count_isolates_an_overflow_error():
    assert tribe._page_count(float("inf")) == 0


def test_collect_raises_when_every_item_fails_to_parse(window):
    http = FakeHttp({CONFIG.url: json.dumps({"events": [{"title": "No date"}], "total_pages": 1})})
    with pytest.raises(SourceError, match="could not parse any items"):
        tribe.collect(CONFIG, http, window)


def test_collect_empty_feed_is_ok(window):
    http = FakeHttp({CONFIG.url: json.dumps({"events": [], "total_pages": 1})})
    assert tribe.collect(CONFIG, http, window) == []
