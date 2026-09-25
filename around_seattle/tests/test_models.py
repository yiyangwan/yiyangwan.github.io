from datetime import date, datetime, timedelta, timezone

from around_seattle.models import LA, Window, effective_end, in_window, is_ongoing, span_days
from around_seattle.tests.conftest import NOW, make_event


def test_window_starting_uses_pacific_date():
    window = Window.starting(datetime(2026, 9, 25, 22, 30, tzinfo=LA))
    assert window.today == date(2026, 9, 25)
    assert window.near_end == date(2026, 10, 9)
    assert window.far_end == date(2026, 11, 24)
    assert window.now.tzinfo == LA
    # 05:30 UTC on the 26th is still the evening of the 25th in Seattle
    assert Window.starting(datetime(2026, 9, 26, 5, 30, tzinfo=timezone.utc)).today == date(2026, 9, 25)


def test_effective_end_prefers_end_then_defaults():
    timed = make_event(end=None)
    assert effective_end(timed) == timed.start + timedelta(hours=2)
    all_day = make_event(start=datetime(2026, 9, 26, 0, 0, tzinfo=LA), end=None, all_day=True)
    assert effective_end(all_day) == datetime(2026, 9, 27, 0, 0, tzinfo=LA)
    explicit = make_event()
    assert effective_end(explicit) == explicit.end


def test_in_window_drops_ended_and_too_far_events():
    window = Window.starting(NOW)
    assert in_window(make_event(), window)
    ended = make_event(start=datetime(2026, 9, 24, 18, 0, tzinfo=LA), end=datetime(2026, 9, 24, 20, 0, tzinfo=LA))
    assert not in_window(ended, window)
    too_far = make_event(start=datetime(2026, 11, 25, 18, 0, tzinfo=LA), end=None)
    assert not in_window(too_far, window)
    last_day = make_event(start=datetime(2026, 11, 24, 18, 0, tzinfo=LA), end=None)
    assert in_window(last_day, window)


def test_span_days_and_ongoing():
    assert span_days(make_event()) == 1
    weekend = make_event(start=datetime(2026, 10, 3, 0, 0, tzinfo=LA), end=datetime(2026, 10, 5, 0, 0, tzinfo=LA),
                         all_day=True)
    assert span_days(weekend) == 2
    assert not is_ongoing(weekend)
    month = make_event(start=datetime(2026, 10, 1, 0, 0, tzinfo=LA), end=datetime(2026, 11, 1, 0, 0, tzinfo=LA),
                       all_day=True)
    assert span_days(month) == 31
    assert is_ongoing(month)
