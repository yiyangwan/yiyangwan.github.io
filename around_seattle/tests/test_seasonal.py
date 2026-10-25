from datetime import date

import pytest

from around_seattle import seasonal

VALID = """
- id: kubota-fall-color
  title: Fall color at Kubota Garden
  summary: Japanese maples color the ponds and hillsides.
  place: Kubota Garden
  city: Seattle
  region: seattle
  category: outdoors
  url: https://www.kubotagarden.org/
  free: true
  from: "10-01"
  to: "11-15"
  source: https://www.kubotagarden.org/
  verified: 2026-09-25
- id: winter-lights
  title: Winter lights
  summary: Lights on winter evenings.
  place: Somewhere
  city: Bellevue
  region: eastside
  category: festival
  url: https://example.org/lights
  from: "11-20"
  to: "01-05"
  source: https://example.org/lights
  verified: 2026-09-25
"""


def write(tmp_path, text):
    path = tmp_path / "seasonal.yml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_valid(tmp_path):
    picks = seasonal.load(write(tmp_path, VALID))
    assert [pick.id for pick in picks] == ["kubota-fall-color", "winter-lights"]
    assert picks[0].free is True
    assert picks[1].free is None
    assert picks[0].verified == "2026-09-25"


@pytest.mark.parametrize("old, new, message", [
    ("region: seattle", "region: tacoma", "bad region or category"),
    ('from: "10-01"', 'from: "10-1"', "from must be MM-DD"),
    ('from: "10-01"', 'from: "04-31"', "from must be a real date"),
    ("url: https://www.kubotagarden.org/", "url: javascript:alert(1)", "url and source must be http"),
    ("  title: Fall color at Kubota Garden\n", "", "missing title"),
])
def test_load_rejects_bad_entries(tmp_path, old, new, message):
    with pytest.raises(ValueError, match=message):
        seasonal.load(write(tmp_path, VALID.replace(old, new, 1)))


def test_active_and_until_with_year_wrap(tmp_path):
    picks = seasonal.load(write(tmp_path, VALID))
    assert [pick.id for pick in seasonal.shown(picks, date(2026, 10, 15), lookahead_days=0)] == ["kubota-fall-color"]
    assert [pick.id for pick in seasonal.shown(picks, date(2026, 12, 31), lookahead_days=0)] == ["winter-lights"]
    assert [pick.id for pick in seasonal.shown(picks, date(2027, 1, 3), lookahead_days=0)] == ["winter-lights"]
    assert seasonal.shown(picks, date(2026, 9, 25), lookahead_days=0) == []
    assert seasonal.until(picks[0], date(2026, 10, 15)) == date(2026, 11, 15)
    assert seasonal.until(picks[1], date(2026, 12, 31)) == date(2027, 1, 5)
    assert seasonal.until(picks[1], date(2027, 1, 3)) == date(2027, 1, 5)


def test_active_lists_the_picks_ending_soonest_first(tmp_path):
    text = VALID.replace('from: "11-20"\n  to: "01-05"', 'from: "10-01"\n  to: "10-31"')
    picks = seasonal.load(write(tmp_path, text))
    assert [pick.id for pick in seasonal.shown(picks, date(2026, 10, 15), lookahead_days=0)] == ["winter-lights", "kubota-fall-color"]


def test_match_is_optional_and_normalized(tmp_path):
    picks = seasonal.load(write(tmp_path, VALID.replace("  free: true\n", "  free: true\n  match: [Kubota Fall Tour]\n", 1)))
    assert picks[0].match == ("kubota fall tour",)
    assert picks[1].match == ()
    with pytest.raises(ValueError, match="match must be a list"):
        seasonal.load(write(tmp_path, VALID.replace("  free: true\n", "  free: true\n  match: Kubota\n", 1)))


def test_absorb_drops_feed_listings_of_an_active_pick(tmp_path):
    from datetime import datetime
    from around_seattle.models import LA
    from around_seattle.tests.conftest import make_event
    picks = seasonal.load(write(tmp_path, VALID.replace("  free: true\n", "  free: true\n  match: [Maple Walk]\n", 1)))
    feed = [
        make_event(uid="1", title="Kubota Maple Walk", region="seattle", start=datetime(2026, 10, 20, 10, 0, tzinfo=LA)),
        make_event(uid="2", title="Kubota Maple Walk", region="seattle", start=datetime(2026, 12, 20, 10, 0, tzinfo=LA)),
        make_event(uid="3", title="Kubota Maple Walk", region="eastside", start=datetime(2026, 10, 20, 10, 0, tzinfo=LA)),
        make_event(uid="4", title="Fall color at Kubota Garden", start=datetime(2026, 10, 21, 10, 0, tzinfo=LA)),
        make_event(uid="5", title="Garden Concert", region="seattle", start=datetime(2026, 10, 20, 10, 0, tzinfo=LA)),
    ]
    assert [e.uid for e in seasonal.absorb(feed, picks)] == ["2", "3", "5"]


def test_opens_is_the_first_day_of_the_current_or_next_window(tmp_path):
    kubota, lights = seasonal.load(write(tmp_path, VALID))
    assert seasonal.opens(kubota, date(2026, 9, 20)) == date(2026, 10, 1)
    assert seasonal.opens(kubota, date(2026, 10, 15)) == date(2026, 10, 1)
    assert seasonal.opens(lights, date(2026, 11, 10)) == date(2026, 11, 20)
    assert seasonal.opens(lights, date(2027, 1, 3)) == date(2026, 11, 20)  # the window wraps the new year


def test_shown_adds_picks_opening_within_two_weeks(tmp_path):
    picks = seasonal.load(write(tmp_path, VALID))
    assert [p.id for p in seasonal.shown(picks, date(2026, 9, 17))] == ["kubota-fall-color"]  # opens in 14 days
    assert seasonal.shown(picks, date(2026, 9, 16)) == []
    assert [p.id for p in seasonal.shown(picks, date(2026, 11, 10))] == ["kubota-fall-color", "winter-lights"]
