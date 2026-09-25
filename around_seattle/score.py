"""Deterministic 0 to 100 score used to rank events within a day."""
from __future__ import annotations

import re

from .models import Event, span_days

TYPE_WEIGHTS = {"festival": 30, "music": 26, "market": 26, "outdoors": 26, "arts": 15, "other": 5}
MULTI_DAY_BONUS = 6
WEEKEND_BONUS = 5
FREE_BONUS = 3
ANNUAL_BONUS = 3
RECURRING_PENALTY = 12
LOW_VALUE_PENALTY = 10
FRIDAY_EVENING_HOUR = 17
ANNUAL = re.compile(r"\bannual\b", re.IGNORECASE)
LOW_VALUE = re.compile(r"\b(?:trivia|bingo|happy hours?|drop-in|open mics?|karaoke|line dancing)\b", re.IGNORECASE)


def score(event: Event, source_weight: int) -> int:
    total = source_weight + TYPE_WEIGHTS.get(event.category, TYPE_WEIGHTS["other"])
    if 2 <= span_days(event) <= 4:
        total += MULTI_DAY_BONUS
    weekday = event.start.weekday()
    if weekday >= 5 or (weekday == 4 and (event.all_day or event.start.hour >= FRIDAY_EVENING_HOUR)):
        total += WEEKEND_BONUS
    if event.free:
        total += FREE_BONUS
    if ANNUAL.search(event.title):
        total += ANNUAL_BONUS
    if len(event.more_dates) >= 2:  # three or more occurrences in the 60-day window
        total -= RECURRING_PENALTY
    if LOW_VALUE.search(event.title):
        total -= LOW_VALUE_PENALTY
    return max(0, min(100, total))
