from datetime import datetime

from around_seattle.dedupe import collapse_recurring, merge_duplicates, normalize_title
from around_seattle.models import LA
from around_seattle.tests.conftest import make_event


def test_normalize_title():
    assert normalize_title("The 2026 Halloween Pet Parade!") == "halloween pet parade"
    assert normalize_title("Ignite Seattle #52") == "ignite seattle 52"
    assert normalize_title("Brown’s Happy Hour 2026") == "browns happy hour"


def test_merge_prefers_heavier_source_and_fills_gaps():
    light = make_event(source_id="uw-seattle", uid="a", url="https://example.org/a", venue=None)
    heavy = make_event(source_id="town-hall", uid="b", url=None, venue="Town Hall")
    merged = merge_duplicates([light, heavy], {"uw-seattle": 10, "town-hall": 30})
    assert len(merged) == 1
    assert merged[0].source_id == "town-hall"
    assert merged[0].url == "https://example.org/a"
    assert merged[0].venue == "Town Hall"


def test_merge_keeps_other_sessions_on_the_same_day_as_more_dates():
    early = make_event(uid="a", start=datetime(2026, 9, 26, 10, 0, tzinfo=LA), end=None)
    late = make_event(uid="b", start=datetime(2026, 9, 26, 14, 0, tzinfo=LA), end=None)
    merged = merge_duplicates([late, early], {"test": 20})
    assert [event.start.hour for event in merged] == [10]
    assert merged[0].more_dates == (datetime(2026, 9, 26, 14, 0, tzinfo=LA),)


def test_merge_keeps_same_day_pairs_in_different_regions_apart():
    seattle = make_event(uid="s", city="Seattle", region="seattle")
    bellevue = make_event(uid="b", city="Bellevue", region="eastside")
    merged = merge_duplicates([seattle, bellevue], {"test": 20})
    assert sorted((event.uid, event.region, event.more_dates) for event in merged) == [
        ("b", "eastside", ()), ("s", "seattle", ())]


def test_collapse_recurring_series_by_title_and_venue():
    weekly = [make_event(uid=str(i), title="Trivia Night", venue="Pub", end=None,
                         start=datetime(2026, 10, 1 + 7 * i, 19, 0, tzinfo=LA)) for i in range(4)]
    elsewhere = make_event(uid="x", title="Trivia Night", venue="Another Pub", end=None,
                           start=datetime(2026, 10, 2, 19, 0, tzinfo=LA))
    collapsed = collapse_recurring(weekly + [elsewhere])
    assert len(collapsed) == 2
    series = next(event for event in collapsed if event.venue == "Pub")
    assert series.start == datetime(2026, 10, 1, 19, 0, tzinfo=LA)
    assert len(series.more_dates) == 3


def test_collapse_recurring_ignores_city_when_venue_matches():
    nights = [make_event(uid=letter, title="Trivia Night", venue="Pub", city=city, end=None,
                         start=datetime(2026, 10, day, 19, 0, tzinfo=LA))
             for letter, city, day in [("a", "Seattle", 1), ("b", None, 8), ("c", None, 15)]]
    collapsed = collapse_recurring(nights)
    assert len(collapsed) == 1
    assert collapsed[0].start == datetime(2026, 10, 1, 19, 0, tzinfo=LA)
    assert len(collapsed[0].more_dates) == 2


def test_collapse_recurring_keeps_same_title_in_different_cities_apart():
    seattle = make_event(uid="s", title="Farmers Market", venue=None, city="Seattle", region="seattle", end=None,
                         start=datetime(2026, 9, 27, 10, 0, tzinfo=LA))
    redmond = make_event(uid="r", title="Farmers Market", venue=None, city="Redmond", region="eastside", end=None,
                         start=datetime(2026, 9, 28, 10, 0, tzinfo=LA))
    collapsed = collapse_recurring([seattle, redmond])
    assert [(event.city, event.more_dates) for event in collapsed] == [("Seattle", ()), ("Redmond", ())]
