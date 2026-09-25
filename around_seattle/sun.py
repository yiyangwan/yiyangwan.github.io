"""Sunrise and sunset for Seattle, one entry per day in the near window."""
from __future__ import annotations

from datetime import datetime, timedelta

from astral import LocationInfo
from astral.sun import sun

from .models import LA, Window

SEATTLE = LocationInfo("Seattle", "USA", "America/Los_Angeles", 47.6062, -122.3321)


def _to_minute(value: datetime) -> str:
    return (value + timedelta(seconds=30)).replace(second=0, microsecond=0).isoformat()


def for_window(window: Window) -> dict[str, dict[str, str]]:
    days = {}
    day = window.today
    while day <= window.near_end:
        times = sun(SEATTLE.observer, date=day, tzinfo=LA)
        days[day.isoformat()] = {"sunrise": _to_minute(times["sunrise"]), "sunset": _to_minute(times["sunset"])}
        day += timedelta(days=1)
    return days
