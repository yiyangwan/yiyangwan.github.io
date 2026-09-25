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
    ("url: https://www.kubotagarden.org/", "url: javascript:alert(1)", "url and source must be http"),
    ("  title: Fall color at Kubota Garden\n", "", "missing title"),
])
def test_load_rejects_bad_entries(tmp_path, old, new, message):
    with pytest.raises(ValueError, match=message):
        seasonal.load(write(tmp_path, VALID.replace(old, new, 1)))


def test_active_and_until_with_year_wrap(tmp_path):
    picks = seasonal.load(write(tmp_path, VALID))
    assert [pick.id for pick in seasonal.active(picks, date(2026, 10, 15))] == ["kubota-fall-color"]
    assert [pick.id for pick in seasonal.active(picks, date(2026, 12, 31))] == ["winter-lights"]
    assert [pick.id for pick in seasonal.active(picks, date(2027, 1, 3))] == ["winter-lights"]
    assert seasonal.active(picks, date(2026, 9, 25)) == []
    assert seasonal.until(picks[0], date(2026, 10, 15)) == date(2026, 11, 15)
    assert seasonal.until(picks[1], date(2026, 12, 31)) == date(2027, 1, 5)
    assert seasonal.until(picks[1], date(2027, 1, 3)) == date(2027, 1, 5)
