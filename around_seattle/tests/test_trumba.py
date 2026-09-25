from datetime import datetime

import pytest

from around_seattle.models import LA, SourceError
from around_seattle.sources import trumba_ics
from around_seattle.tests.conftest import FakeHttp, make_config, read_fixture

CONFIG = make_config(id="seattle-gov", url="https://www.trumba.com/calendars/seattlegov-city-wide.ics")


def by_uid(events):
    return {event.uid.rsplit("/", 1)[-1]: event for event in events}


def parsed():
    return by_uid(trumba_ics.parse(read_fixture("trumba_seattle.ics"), CONFIG))


def test_collect_keeps_events_in_window(window):
    http = FakeHttp({CONFIG.url: read_fixture("trumba_seattle.ics")})
    events = by_uid(trumba_ics.collect(CONFIG, http, window))
    assert sorted(events) == ["1001", "1002", "1003", "1004", "1006"]  # 1005 ended before the window
    assert http.calls[0][2] == {"min_interval": 0.0, "respect_robots": True}


def test_timed_event_fields():
    event = parsed()["1001"]
    assert event.source_id == "seattle-gov"
    assert event.title == "Mid-Autumn Lantern Walk"
    assert event.start == datetime(2026, 9, 26, 18, 0, tzinfo=LA)
    assert event.end == datetime(2026, 9, 26, 20, 0, tzinfo=LA)
    assert event.all_day is False
    assert event.venue == "Volunteer Park"
    assert event.location_text == "Volunteer Park, 1247 15th Ave E Seattle WA 98112"
    assert event.url == "https://www.seattle.gov/event-calendar?trumbaEmbed=view%3Devent%26eventid%3D1001"
    assert (event.price, event.free) == ("Free", True)
    assert event.raw_categories == ("Parks & Recreation", "Festivals/Fairs", "Ethnic/Cultural", "Outdoor")
    assert event.summary == "Carry a paper lantern through the park at dusk."


def test_all_day_event_uses_exclusive_end():
    event = parsed()["1003"]
    assert event.all_day is True
    assert event.start == datetime(2026, 9, 25, 0, 0, tzinfo=LA)
    assert event.end == datetime(2026, 10, 1, 0, 0, tzinfo=LA)
    assert event.venue == "Elisabeth Miller Library"
    assert event.summary == "Botanical watercolors on display."


def test_equal_end_becomes_none_and_entities_decode():
    event = parsed()["1004"]
    assert event.title == "Chinatown–International District Walking Tour"
    assert event.end is None
    assert (event.price, event.free) == ("$22", False)
    assert event.url == "https://example.org/cid-walk"  # no X-TRUMBA-LINK, falls back to URL


def test_unsafe_urls_are_dropped():
    assert parsed()["1006"].url is None


def test_invalid_calendar_raises_source_error():
    with pytest.raises(SourceError, match="invalid iCal"):
        trumba_ics.parse("<!DOCTYPE html><html>Just a moment...</html>", CONFIG)


def test_summary_strips_markup_runs():
    ics = ("BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Trivia Night\n"
          "DTSTART;TZID=America/Los_Angeles:20260926T190000\n"
          "DESCRIPTION:** 6:00 p.m. ** doors\nUID:markup-1\nEND:VEVENT\nEND:VCALENDAR\n")
    event = trumba_ics.parse(ics, CONFIG)[0]
    assert event.summary == "6:00 p.m. doors"
