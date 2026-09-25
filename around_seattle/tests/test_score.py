from datetime import datetime

import pytest

from around_seattle.models import LA
from around_seattle.score import score
from around_seattle.tests.conftest import make_event

WEDNESDAY = dict(start=datetime(2026, 9, 30, 12, 0, tzinfo=LA), end=datetime(2026, 9, 30, 14, 0, tzinfo=LA),
                 category="festival")


def test_base_score_is_source_plus_type():
    assert score(make_event(**WEDNESDAY), 20) == 50


@pytest.mark.parametrize("changes, expected", [
    (dict(start=datetime(2026, 10, 3, 12, 0, tzinfo=LA), end=datetime(2026, 10, 3, 14, 0, tzinfo=LA)), 55),
    (dict(start=datetime(2026, 10, 2, 19, 0, tzinfo=LA), end=datetime(2026, 10, 2, 21, 0, tzinfo=LA)), 55),
    (dict(start=datetime(2026, 10, 2, 10, 0, tzinfo=LA), end=datetime(2026, 10, 2, 12, 0, tzinfo=LA)), 50),
    (dict(free=True), 53),
    (dict(title="12th Annual Harvest Fair"), 53),
    (dict(more_dates=(datetime(2026, 10, 7, 12, 0, tzinfo=LA), datetime(2026, 10, 14, 12, 0, tzinfo=LA))), 38),
    (dict(title="Trivia Night"), 40),
    (dict(category="arts"), 35),
    (dict(category="other"), 25),
])
def test_score_adjustments(changes, expected):
    assert score(make_event(**{**WEDNESDAY, **changes}), 20) == expected


def test_multi_day_bonus_only_for_two_to_four_days():
    two_days = make_event(start=datetime(2026, 9, 30, 0, 0, tzinfo=LA), end=datetime(2026, 10, 2, 0, 0, tzinfo=LA),
                          all_day=True, category="festival")
    six_days = make_event(start=datetime(2026, 9, 28, 0, 0, tzinfo=LA), end=datetime(2026, 10, 4, 0, 0, tzinfo=LA),
                          all_day=True, category="festival")
    assert score(two_days, 20) == 56
    assert score(six_days, 20) == 50


def test_score_is_clamped():
    assert score(make_event(**WEDNESDAY), 95) == 100
    assert score(make_event(**{**WEDNESDAY, "category": "other", "title": "Bingo"}), 0) == 0
