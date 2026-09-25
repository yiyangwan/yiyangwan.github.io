"""Cross-source duplicate merge and recurring-series collapse."""
from __future__ import annotations

import re
from dataclasses import replace

from .models import Event

MAX_MORE_DATES = 6
_FILLABLE = ("venue", "location_text", "city", "url", "summary", "price", "free")


def normalize_title(title: str) -> str:
    text = re.sub(r"[‘’'`]", "", title.casefold())
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"^\s*(?:the\s+)?(?:(?:19|20)\d{2}\s+)?", "", text)  # leading "the" and/or year
    text = re.sub(r"\s+(?:19|20)\d{2}\s*$", "", text)  # trailing year
    return " ".join(text.split())


def _fill(primary: Event, other: Event) -> Event:
    updates = {name: getattr(other, name) for name in _FILLABLE
               if getattr(primary, name) in (None, "") and getattr(other, name) not in (None, "")}
    return replace(primary, **updates) if updates else primary


def merge_duplicates(events: list[Event], weights: dict[str, int]) -> list[Event]:
    """One event per (title, start date, region). The heavier source wins; later start times become more_dates."""
    groups: dict[tuple, list[Event]] = {}
    for event in events:
        groups.setdefault((normalize_title(event.title), event.start.date(), event.region), []).append(event)
    merged = []
    for group in groups.values():
        ranked = sorted(group, key=lambda e: (-weights.get(e.source_id, 0), e.start, e.source_id, e.uid))
        best = ranked[0]
        for other in ranked[1:]:
            best = _fill(best, other)
        later = sorted({e.start for e in group if e.start > best.start} | set(best.more_dates))
        merged.append(replace(best, more_dates=tuple(later)))
    return sorted(merged, key=lambda e: (e.start, e.title))


def collapse_recurring(events: list[Event]) -> list[Event]:
    """Collapse a repeating series (same title, venue, and region) into its next occurrence.

    The key falls back to city only when venue is empty, so a cross-listed night that gained a
    city string does not split off from a series that otherwise shares a venue.
    """
    groups: dict[tuple, list[Event]] = {}
    for event in events:
        key = (normalize_title(event.title),
               (event.venue or "").casefold() or "city:" + (event.city or "").casefold(),
               event.region or "")
        groups.setdefault(key, []).append(event)
    collapsed = []
    for group in groups.values():
        ordered = sorted(group, key=lambda e: e.start)
        first = ordered[0]
        later = {e.start for e in ordered[1:]} | {d for e in ordered for d in e.more_dates}
        collapsed.append(replace(first, more_dates=tuple(sorted(d for d in later if d > first.start))))
    return sorted(collapsed, key=lambda e: (e.start, e.title))
