from datetime import date, datetime

import pytest

from around_seattle import signature
from around_seattle.models import LA, Window
from around_seattle.tests.conftest import make_event

VALID = """
- id: coffee-festival
  title: Seattle Coffee Festival
  summary: Specialty roasters pour tastings in a Magnuson Park hangar.
  place: Magnuson Park Hangar 30
  city: Seattle
  region: seattle
  category: market
  url: https://www.seattlecoffeefestival.com/
  free: false
  usually: late October
  dates:
    - {from: 2026-10-24, to: 2026-10-25, source: "https://www.seattlecoffeefestival.com/", verified: 2026-10-24}
- id: tree-lighting
  title: Tree Lighting Celebration at Westlake Park
  summary: The city's holiday season opens with a tree lighting downtown.
  place: Westlake Park
  city: Seattle
  region: seattle
  category: festival
  url: https://www.downtownseattle.org/events/
  usually: the day after Thanksgiving
  match: [Westlake Tree Lighting]
  dates:
    - {from: 2025-11-28, to: 2025-11-28, source: "https://www.downtownseattle.org/events/", verified: 2025-11-01}
    - {from: 2026-11-27, to: 2026-11-27, starts: "17:00", ends: "19:30",
       source: "https://www.downtownseattle.org/events/", verified: 2026-10-24}
- id: folklife
  title: Northwest Folklife Festival
  summary: Music, dance, and food from many cultures across Seattle Center.
  place: Seattle Center
  city: Seattle
  region: seattle
  category: festival
  url: https://www.nwfolklife.org/
  free: true
  usually: Memorial Day weekend
  dates: []
"""
NOW = datetime(2026, 10, 24, 8, 0, tzinfo=LA)


def write(tmp_path, text):
    path = tmp_path / "signature.yml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def picks(tmp_path):
    return signature.load(write(tmp_path, VALID))


def test_load_valid(picks):
    coffee, lighting, folklife = picks
    assert (coffee.id, coffee.free, coffee.usually) == ("coffee-festival", False, "late October")
    assert coffee.dates[0].first == date(2026, 10, 24)
    assert coffee.dates[0].last == date(2026, 10, 25)
    assert coffee.dates[0].verified == "2026-10-24"
    assert lighting.free is None
    assert lighting.match == ("westlake tree lighting",)
    assert [o.first for o in lighting.dates] == [date(2025, 11, 28), date(2026, 11, 27)]
    assert lighting.dates[1].starts.hour == 17 and lighting.dates[1].ends.minute == 30
    assert folklife.dates == ()


@pytest.mark.parametrize("old, new, message", [
    ("  title: Seattle Coffee Festival\n", "", "missing title"),
    ("  usually: late October\n", "", "missing usually"),
    ("region: seattle\n  category: market", "region: tacoma\n  category: market", "bad region or category"),
    ("category: market", "category: sports", "bad region or category"),
    ("url: https://www.seattlecoffeefestival.com/\n", "url: javascript:alert(1)\n", "url must be http"),
    ('source: "https://www.seattlecoffeefestival.com/"', 'source: "ftp://example.org"', "source must be http"),
    ("{from: 2026-10-24, to: 2026-10-25", "{from: 2026-10-26, to: 2026-10-25", "from is after to"),
    ("{from: 2026-10-24,", '{from: "Oct 24",', "from must be a date"),
    ('starts: "17:00"', "starts: 17:00", "starts must be a quoted HH:MM time"),
    ('ends: "19:30"', 'ends: "7:30 pm"', "ends must be a quoted HH:MM time"),
    ('starts: "17:00", ends: "19:30",', 'starts: "17:00",', "starts and ends go together"),
    ('ends: "19:30"', 'ends: "16:00"', "ends before it starts"),
    ("verified: 2026-10-24}\n- id: tree", "verified: }\n- id: tree", "missing verified"),
    ("  dates: []\n", "  dates: soon\n", "dates must be a list"),
    ("match: [Westlake Tree Lighting]", "match: Westlake", "match must be a list"),
])
def test_load_rejects_bad_entries(tmp_path, old, new, message):
    assert old in VALID
    with pytest.raises(ValueError, match=message):
        signature.load(write(tmp_path, VALID.replace(old, new, 1)))


def test_load_rejects_duplicate_ids_and_bad_shapes(tmp_path):
    with pytest.raises(ValueError, match="duplicate id coffee-festival"):
        signature.load(write(tmp_path, VALID + VALID.split("- id: tree-lighting")[0]))
    with pytest.raises(ValueError, match="expected a list"):
        signature.load(write(tmp_path, "id: x\n"))
    with pytest.raises(ValueError, match="expected a mapping"):
        signature.load(write(tmp_path, "- just a string\n"))
    with pytest.raises(ValueError, match="date #0: expected a mapping"):
        signature.load(write(tmp_path, VALID.replace("  dates: []\n", "  dates: [2027-05-28]\n")))
    assert signature.load(write(tmp_path, "")) == []


def test_events_in_window(picks):
    events = signature.events(picks, Window.starting(NOW))
    assert [(e.title, e.start, e.end, e.all_day) for e in events] == [
        ("Seattle Coffee Festival", datetime(2026, 10, 24, 0, 0, tzinfo=LA), datetime(2026, 10, 26, 0, 0, tzinfo=LA),
         True),
        ("Tree Lighting Celebration at Westlake Park", datetime(2026, 11, 27, 17, 0, tzinfo=LA),
         datetime(2026, 11, 27, 19, 30, tzinfo=LA), False),
    ]
    coffee = events[0]
    assert (coffee.source_id, coffee.highlight, coffee.score) == ("signature", True, signature.SCORE)
    assert (coffee.venue, coffee.city, coffee.region, coffee.category) == (
        "Magnuson Park Hangar 30", "Seattle", "seattle", "market")
    assert (coffee.url, coffee.free) == ("https://www.seattlecoffeefestival.com/", False)
    assert coffee.summary == "Specialty roasters pour tastings in a Magnuson Park hangar."
    assert coffee.uid == "signature:coffee-festival:2026-10-24"


def test_events_drop_ended_and_far_occurrences(picks):
    after_the_festival = Window.starting(datetime(2026, 10, 26, 0, 0, tzinfo=LA))
    assert [e.title for e in signature.events(picks, after_the_festival)] == [
        "Tree Lighting Celebration at Westlake Park"]
    after_the_lighting = Window.starting(datetime(2026, 11, 27, 19, 30, tzinfo=LA))
    assert signature.events(picks, after_the_lighting) == []
    in_september = Window.starting(datetime(2026, 9, 1, 8, 0, tzinfo=LA))  # the far window ends October 31
    assert [e.title for e in signature.events(picks, in_september)] == ["Seattle Coffee Festival"]


def test_absorb_drops_feed_listings_of_a_signature_event(picks):
    feed = [
        make_event(uid="1", title="Seattle Coffee Festival 2026", start=datetime(2026, 10, 25, 9, 0, tzinfo=LA), end=None),
        make_event(uid="2", title="Seattle Center Westlake Tree Lighting", region="seattle",
                   start=datetime(2026, 11, 27, 17, 0, tzinfo=LA), end=None),
        make_event(uid="3", title="Seattle Coffee Festival", start=datetime(2026, 11, 1, 9, 0, tzinfo=LA), end=None),
        make_event(uid="4", title="Seattle Coffee Festival", region="eastside",
                   start=datetime(2026, 10, 24, 9, 0, tzinfo=LA), end=None),
        make_event(uid="5", title="Coffee Tasting", start=datetime(2026, 10, 24, 9, 0, tzinfo=LA), end=None),
    ]
    assert [e.uid for e in signature.absorb(feed, picks)] == ["3", "4", "5"]


def test_needs_dates_lists_entries_without_an_upcoming_date(picks):
    assert [p.id for p in signature.needs_dates(picks, date(2026, 10, 24))] == ["folklife"]
    assert [p.id for p in signature.needs_dates(picks, date(2026, 10, 26))] == ["coffee-festival", "folklife"]
    assert [p.id for p in signature.needs_dates(picks, date(2026, 11, 28))] == [
        "coffee-festival", "tree-lighting", "folklife"]


def test_an_entry_with_several_upcoming_ranges_is_one_event_with_more_dates(tmp_path):
    text = """
- id: santa-trains
  title: Santa Trains
  summary: Holiday train rides with Santa.
  place: Snoqualmie Depot
  city: Snoqualmie
  region: eastside
  category: festival
  url: https://example.org/santa
  usually: weekends after Thanksgiving
  dates:
    - {from: 2026-11-28, to: 2026-11-29, source: "https://example.org/santa", verified: 2026-10-24}
    - {from: 2026-12-04, to: 2026-12-06, source: "https://example.org/santa", verified: 2026-10-24}
    - {from: 2026-12-11, to: 2026-12-13, source: "https://example.org/santa", verified: 2026-10-24}
"""
    picks = signature.load(write(tmp_path, text))
    events = signature.events(picks, Window.starting(datetime(2026, 11, 20, 8, 0, tzinfo=LA)))
    assert len(events) == 1
    assert (events[0].start, events[0].end) == (datetime(2026, 11, 28, 0, 0, tzinfo=LA),
                                                datetime(2026, 11, 30, 0, 0, tzinfo=LA))
    assert events[0].more_dates == (datetime(2026, 12, 4, 0, 0, tzinfo=LA), datetime(2026, 12, 11, 0, 0, tzinfo=LA))
    assert events[0].more_ends == (datetime(2026, 12, 7, 0, 0, tzinfo=LA), datetime(2026, 12, 14, 0, 0, tzinfo=LA))
    later = signature.events(picks, Window.starting(datetime(2026, 12, 1, 8, 0, tzinfo=LA)))
    assert [(e.start.day, len(e.more_dates)) for e in later] == [(4, 1)]


def test_needs_recheck_lists_dates_starting_soon_that_were_checked_long_ago(tmp_path):
    text = VALID.replace("verified: 2026-10-24}\n- id: tree", "verified: 2026-06-01}\n- id: tree", 1)
    picks = signature.load(write(tmp_path, text))
    assert [(p.id, when.verified) for p, when in signature.needs_recheck(picks, date(2026, 10, 1))] == [
        ("coffee-festival", "2026-06-01")]
    assert signature.needs_recheck(picks, date(2026, 9, 1)) == []  # more than 30 days before it starts
    assert signature.needs_recheck(picks, date(2026, 10, 26)) == []  # it has ended
    assert signature.needs_recheck(picks, date(2026, 11, 20)) == []  # the lighting was checked recently


def test_verified_must_be_a_date(tmp_path):
    with pytest.raises(ValueError, match="verified must be a date"):
        signature.load(write(tmp_path, VALID.replace("verified: 2026-10-24}", 'verified: "last week"}', 1)))


def test_load_rejects_overlapping_date_ranges(tmp_path):
    text = VALID.replace('{from: 2025-11-28, to: 2025-11-28,', '{from: 2026-11-26, to: 2026-11-27,', 1)
    with pytest.raises(ValueError, match="signature event tree-lighting: date ranges overlap"):
        signature.load(write(tmp_path, text))


def test_absorb_matches_a_feed_listing_that_overlaps_a_range(picks):
    early = make_event(uid="1", title="Seattle Coffee Festival", all_day=True,
                       start=datetime(2026, 10, 23, 0, 0, tzinfo=LA), end=datetime(2026, 10, 26, 0, 0, tzinfo=LA))
    undated = make_event(uid="2", title="Northwest Folklife Festival", start=datetime(2026, 10, 24, 11, 0, tzinfo=LA))
    assert [e.uid for e in signature.absorb([early, undated], picks)] == ["2"]


def test_needs_recheck_boundaries(tmp_path):
    def picks_verified(verified):
        return signature.load(write(tmp_path, VALID.replace("verified: 2026-10-24}\n- id: tree",
                                                            f"verified: {verified}}}\n- id: tree", 1)))
    starts_in_30_days, starts_in_31_days = date(2026, 9, 24), date(2026, 9, 23)
    assert [p.id for p, _ in signature.needs_recheck(picks_verified("2026-06-01"), starts_in_30_days)] == [
        "coffee-festival"]
    assert signature.needs_recheck(picks_verified("2026-06-01"), starts_in_31_days) == []
    assert signature.needs_recheck(picks_verified("2026-06-26"), starts_in_30_days) == []  # checked 90 days ago
    assert [p.id for p, _ in signature.needs_recheck(picks_verified("2026-06-25"), starts_in_30_days)] == [
        "coffee-festival"]  # checked 91 days ago


def test_an_all_day_range_across_the_fall_dst_change_ends_at_local_midnight(tmp_path):
    text = VALID.replace("{from: 2026-10-24, to: 2026-10-25, source:", "{from: 2026-10-31, to: 2026-11-01, source:", 1)
    events = signature.events(signature.load(write(tmp_path, text)), Window.starting(NOW))
    coffee = next(e for e in events if e.title == "Seattle Coffee Festival")
    assert coffee.end == datetime(2026, 11, 2, 0, 0, tzinfo=LA)
    assert coffee.end.isoformat() == "2026-11-02T00:00:00-08:00"
