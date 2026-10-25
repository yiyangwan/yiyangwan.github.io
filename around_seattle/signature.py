"""Signature annual events from _data/around_seattle/signature.yml: curated, dated, and listed first."""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from pathlib import Path

import yaml

from .dedupe import normalize_title, title_mentions
from .models import CATEGORIES, LA, REGIONS, Event, SignatureDate, SignatureEvent, Window, in_window, last_day
from .text import safe_url

SOURCE_ID = "signature"
SCORE = 95
_REQUIRED = ("id", "title", "summary", "place", "city", "region", "category", "url", "usually")
_DATE_REQUIRED = ("from", "to", "source", "verified")
_CLOCK = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
RECHECK_WITHIN_DAYS = 30  # dates starting this soon
RECHECK_AFTER_DAYS = 90  # and checked longer ago than this should be checked again


def load(path: Path) -> list[SignatureEvent]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a list of signature events")
    picks = [_entry(entry, index) for index, entry in enumerate(raw)]
    seen: set[str] = set()
    for pick in picks:
        if pick.id in seen:
            raise ValueError(f"signature events: duplicate id {pick.id}")
        seen.add(pick.id)
    return picks


def _entry(entry, index: int) -> SignatureEvent:
    if not isinstance(entry, dict):
        raise ValueError(f"signature event #{index}: expected a mapping")
    ident = entry.get("id", f"#{index}")
    missing = [key for key in _REQUIRED if not entry.get(key)]
    if missing:
        raise ValueError(f"signature event {ident}: missing {', '.join(missing)}")
    if entry["region"] not in REGIONS or entry["category"] not in CATEGORIES:
        raise ValueError(f"signature event {ident}: bad region or category")
    if safe_url(entry["url"]) is None:
        raise ValueError(f"signature event {ident}: url must be http(s)")
    dates = entry.get("dates") or []
    if not isinstance(dates, list):
        raise ValueError(f"signature event {ident}: dates must be a list")
    match = entry.get("match") or []
    if not isinstance(match, list):
        raise ValueError(f"signature event {ident}: match must be a list")
    ranges = sorted((_date_range(item, f"signature event {ident} date #{n}") for n, item in enumerate(dates)),
                    key=lambda when: when.first)
    if any(later.first <= earlier.last for earlier, later in zip(ranges, ranges[1:])):
        raise ValueError(f"signature event {ident}: date ranges overlap")
    free = entry.get("free")
    return SignatureEvent(
        id=str(entry["id"]), title=str(entry["title"]), summary=str(entry["summary"]), place=str(entry["place"]),
        city=str(entry["city"]), region=entry["region"], category=entry["category"], url=entry["url"],
        free=free if isinstance(free, bool) else None, usually=str(entry["usually"]),
        match=tuple(normalize_title(str(name)) for name in match), dates=tuple(ranges),
    )


def _date_range(item, where: str) -> SignatureDate:
    if not isinstance(item, dict):
        raise ValueError(f"{where}: expected a mapping")
    missing = [key for key in _DATE_REQUIRED if not item.get(key)]
    if missing:
        raise ValueError(f"{where}: missing {', '.join(missing)}")
    first, last = _day(item["from"], f"{where}: from"), _day(item["to"], f"{where}: to")
    if first > last:
        raise ValueError(f"{where}: from is after to")
    if safe_url(item["source"]) is None:
        raise ValueError(f"{where}: source must be http(s)")
    starts, ends = _clock(item.get("starts"), f"{where}: starts"), _clock(item.get("ends"), f"{where}: ends")
    if (starts is None) != (ends is None):
        raise ValueError(f"{where}: starts and ends go together")
    if starts is not None and first == last and ends <= starts:
        raise ValueError(f"{where}: ends before it starts")
    verified = _day(item["verified"], f"{where}: verified").isoformat()
    return SignatureDate(first=first, last=last, source=item["source"], verified=verified, starts=starts, ends=ends)


def _day(value, where: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"{where} must be a date") from None


def _clock(value, where: str) -> time | None:
    """A quoted "HH:MM"; unquoted, YAML reads 17:00 as the number 1020."""
    if value is None:
        return None
    found = _CLOCK.match(value) if isinstance(value, str) else None
    if found is None:
        raise ValueError(f"{where} must be a quoted HH:MM time")
    return time(int(found.group(1)), int(found.group(2)))


def events(picks: list[SignatureEvent], window: Window) -> list[Event]:
    """One event per entry: its next date range in the window, with the later ones in the window as more dates."""
    listed = []
    for pick in picks:
        upcoming = sorted((event for event in (_event(pick, when) for when in pick.dates) if in_window(event, window)),
                          key=lambda event: event.start)
        if upcoming:
            first, *later = upcoming
            listed.append(replace(first, more_dates=tuple(event.start for event in later),
                                  more_ends=tuple(event.end for event in later)))
    return sorted(listed, key=lambda e: (e.start, e.title))


def _event(pick: SignatureEvent, when: SignatureDate) -> Event:
    if when.starts is None:
        start = datetime.combine(when.first, time(0), tzinfo=LA)
        end = datetime.combine(when.last + timedelta(days=1), time(0), tzinfo=LA)
    else:
        start = datetime.combine(when.first, when.starts, tzinfo=LA)
        end = datetime.combine(when.last, when.ends, tzinfo=LA)
    return Event(
        source_id=SOURCE_ID, uid=f"{SOURCE_ID}:{pick.id}:{when.first.isoformat()}", title=pick.title,
        start=start, end=end, all_day=when.starts is None, venue=pick.place,
        location_text=f"{pick.place}, {pick.city}", city=pick.city, region=pick.region, url=pick.url,
        summary=pick.summary, free=pick.free, category=pick.category, score=SCORE, highlight=True,
    )


def absorb(feed: list[Event], picks: list[SignatureEvent]) -> list[Event]:
    """Drop feed listings of a signature event: its title or a match on one of its dates, in its region."""
    return [event for event in feed if not any(_lists(event, pick) for pick in picks)]


def _lists(event: Event, pick: SignatureEvent) -> bool:
    if event.region not in (None, pick.region) or not title_mentions(event.title, (normalize_title(pick.title),
                                                                                    *pick.match)):
        return False
    first, last = event.start.date(), last_day(event)
    return any(when.first <= last and first <= when.last for when in pick.dates)


def needs_recheck(picks: list[SignatureEvent], today: date) -> list[tuple[SignatureEvent, SignatureDate]]:
    """Entries whose next dates start within 30 days but were checked more than 90 days ago, with those dates."""
    due = []
    for pick in picks:
        upcoming = min((when for when in pick.dates if when.last >= today), key=lambda when: when.first, default=None)
        if (upcoming is not None and (upcoming.first - today).days <= RECHECK_WITHIN_DAYS
                and (today - date.fromisoformat(upcoming.verified)).days > RECHECK_AFTER_DAYS):
            due.append((pick, upcoming))
    return due


def needs_dates(picks: list[SignatureEvent], today: date) -> list[SignatureEvent]:
    """Entries with no dates ending today or later, so their next dates need checking."""
    return [pick for pick in picks if not any(when.last >= today for when in pick.dates)]
