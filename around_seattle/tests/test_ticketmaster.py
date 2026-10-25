import json
from datetime import datetime

import pytest

from around_seattle import build, dedupe
from around_seattle.models import LA, SourceError, SourceResult, SourceSkipped
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


def _listing(name, segment="Music"):
    """The fixture's first concert under another name and segment."""
    item = json.loads(read_fixture("ticketmaster_page0.json"))["_embedded"]["events"][0]
    item["name"] = name
    item["classifications"][0]["segment"]["name"] = segment
    return item


def test_drops_listings_that_are_not_event_tickets():
    item = _listing("WAMU Theater Amplified Access: Kai Wachi (Not an Event Ticket)")
    assert ticketmaster.to_event(item, CONFIG) is None


def test_strips_venue_moves_and_ticket_tiers_so_duplicates_merge():
    moved = ticketmaster.to_event(_listing("Killswitch Engage - MOVED TO THE NEPTUNE"), CONFIG)
    assert moved.title == "Killswitch Engage"
    tiers = [ticketmaster.to_event(_listing(f"Starstuff: A Festival of Solo Artists ({tier} 3 Day Pass)"), CONFIG)
             for tier in ("Odyssey", "Voyager Deluxe")]
    assert [event.title for event in tiers] == ["Starstuff: A Festival of Solo Artists"] * 2
    assert len(dedupe.merge_duplicates(tiers, {"ticketmaster": 20})) == 1


def test_a_festival_listed_per_tier_and_per_day_shows_once(window):
    def festival_pass(uid, tier, day):
        item = _listing(f"Starstuff: A Festival of Solo Artists ({tier})")
        item["id"] = uid
        item["dates"]["start"] = {"localDate": f"2026-10-{day}", "noSpecificTime": True}
        return item

    items = [festival_pass("t1", "Odyssey 3 Day Pass", 23), festival_pass("t2", "Voyager Deluxe 3 Day Pass", 23),
             *(festival_pass(f"d{day}", "Single Day Pass", day) for day in (23, 24, 25))]
    events = tuple(ticketmaster.to_event(item, CONFIG) for item in items)
    kept = build.process([SourceResult(CONFIG, "ok", events)], [CONFIG], window, {"min_score": 50, "max_events": 30})
    assert [(e.title, e.category, e.score, len(e.more_dates)) for e in kept] == [
        ("Starstuff: A Festival of Solo Artists", "festival", 55, 2)]


def test_performances_keep_ticketmasters_category_over_title_words():
    def category(name, segment="Music"):
        return ticketmaster.to_event(_listing(name, segment), CONFIG).category

    assert category("Hail The Sun w/ A Lot Like Birds") == "music"
    assert category("Jane Remover: Live Exhibit") == "music"
    assert category("Hamlet", segment="Arts & Theatre") == "music"
    assert category("Metropolis (1927)", segment="Film") == "music"
    assert category("Starstuff: A Festival of Solo Artists") == "festival"
    assert category("Bumbershoot (Weekend Festival Pass)") == "festival"  # the stripped note still counts
    assert category("Lumen Field Stadium Tours", segment="Miscellaneous") == "other"  # left to the classifier


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


TIERED = make_config(id="ticketmaster", type="ticketmaster", region=None, respect_robots=False,
                     url="https://app.ticketmaster.com/discovery/v2/events.json", secret_env="TICKETMASTER_API_KEY",
                     arena_venues=("Climate Pledge Arena",), major_venues=("Benaroya Hall",),
                     midsize_venues=("Showbox", "Neptune"))


def _tiered(item):
    return ticketmaster.tiered(ticketmaster.to_event(item, TIERED), item, TIERED)


def _at(venue, wiki=False):
    item = _listing("Some Band")
    item["_embedded"]["venues"][0]["name"] = venue
    if wiki:
        item["_embedded"]["attractions"] = [
            {"name": "Some Band", "externalLinks": {"wiki": [{"url": "https://en.wikipedia.org/wiki/Some_Band"}]}}]
    return item


def test_arena_and_major_venue_shows_are_kept_with_a_boost():
    assert _tiered(_at("Climate Pledge Arena")).boost == ticketmaster.ARENA_BOOST
    assert _tiered(_at("Benaroya Hall - S. Mark Taper Auditorium")).boost == ticketmaster.MAJOR_BOOST
    assert ticketmaster.ARENA_BOOST > ticketmaster.MAJOR_BOOST > ticketmaster.MIDSIZE_BOOST


def test_an_act_with_a_wikipedia_page_adds_to_the_boost():
    assert _tiered(_at("Climate Pledge Arena", wiki=True)).boost == ticketmaster.ARENA_BOOST + ticketmaster.NOTABLE_BOOST


def test_midsize_venue_shows_need_an_act_with_a_wikipedia_page():
    assert _tiered(_at("Showbox SODO")) is None
    expected = ticketmaster.MIDSIZE_BOOST + ticketmaster.NOTABLE_BOOST
    assert _tiered(_at("The Showbox", wiki=True)).boost == expected
    assert _tiered(_at("Neptune Theatre", wiki=True)).boost == expected


def test_other_venues_are_dropped_when_tiers_are_configured():
    assert _tiered(_at("Nectar Lounge", wiki=True)) is None
    untiered = _at("Nectar Lounge")
    assert ticketmaster.tiered(ticketmaster.to_event(untiered, CONFIG), untiered, CONFIG).boost == 0  # no tiers: keep


def test_malformed_attractions_count_as_no_wikipedia_page():
    item = _at("The Showbox")
    item["_embedded"]["attractions"] = ["Some Band", {"externalLinks": ["wiki"]}, {"externalLinks": {"wiki": []}}]
    assert _tiered(item) is None


def test_a_page_of_shows_at_unlisted_venues_is_empty_not_failed(window):
    config = make_config(id="ticketmaster", type="ticketmaster", region=None, respect_robots=False, url=CONFIG.url,
                         secret_env="TICKETMASTER_API_KEY", arena_venues=("Lumen Field",))
    http = FakeHttp({CONFIG.url: read_fixture("ticketmaster_page0.json")})
    assert ticketmaster.collect(config, http, window, env=ENV) == []
