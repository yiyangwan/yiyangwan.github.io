from datetime import datetime

import pytest

from around_seattle.models import LA, SourceError
from around_seattle.sources import civicplus
from around_seattle.tests.conftest import FakeHttp, make_config, read_fixture

CONFIG = make_config(id="redmond-city", type="civicplus", region="eastside",
                     url="https://www.redmond.gov/RSSFeed.aspx?ModID=58&CID=Community-Events-22")


def parsed():
    return {event.title: event for event in civicplus.parse(read_fixture("civicplus_redmond.xml"), CONFIG)}


def test_timed_event_from_namespaced_fields():
    event = parsed()["2nd Annual Flapjacks & Flannel Breakfast"]
    assert event.start == datetime(2026, 10, 3, 9, 30, tzinfo=LA)
    assert event.end == datetime(2026, 10, 3, 12, 0, tzinfo=LA)
    assert event.all_day is False
    assert event.location_text == "8703 160th Ave NE, Redmond, WA 98052"
    assert event.venue == "8703 160th Ave NE"
    assert event.url == "https://www.redmond.gov/Calendar.aspx?EID=3538"
    assert event.summary is None


def test_multi_day_event_without_times_is_all_day():
    event = parsed()["Salmon Days Festival"]
    assert event.all_day is True
    assert event.start == datetime(2026, 10, 3, 0, 0, tzinfo=LA)
    assert event.end == datetime(2026, 10, 5, 0, 0, tzinfo=LA)
    assert event.location_text == "Downtown Issaquah, Issaquah, WA"


def test_items_without_parseable_dates_are_skipped():
    titles = parsed()
    assert "Date TBD Event" not in titles
    assert "City Council Business Meeting" in titles  # noise is filtered later, in build


def test_collect_applies_window(window):
    http = FakeHttp({CONFIG.url: read_fixture("civicplus_redmond.xml")})
    titles = [event.title for event in civicplus.collect(CONFIG, http, window)]
    assert titles == ["2nd Annual Flapjacks & Flannel Breakfast", "Salmon Days Festival",
                      "City Council Business Meeting"]


def test_bot_challenge_page_raises():
    with pytest.raises(SourceError, match="not an RSS feed"):
        civicplus.parse(read_fixture("cloudflare_challenge.html"), CONFIG)


def test_malformed_xml_raises():
    with pytest.raises(SourceError, match="invalid RSS"):
        civicplus.parse("<?xml version='1.0'?><rss><channel><item>", CONFIG)


def test_entity_declarations_are_refused():
    bomb = ('<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY a "aaaa">]>'
            '<rss><channel><item><title>&a;</title></item></channel></rss>')
    with pytest.raises(SourceError, match="invalid RSS"):
        civicplus.parse(bomb, CONFIG)
