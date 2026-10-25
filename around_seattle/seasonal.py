"""Curated seasonal picks from _data/around_seattle/seasonal.yml."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

from .dedupe import normalize_title, title_mentions
from .models import CATEGORIES, NEAR_DAYS, REGIONS, Event, SeasonalPick
from .text import safe_url

_MONTH_DAY = re.compile(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
_REQUIRED = ("id", "title", "summary", "place", "city", "region", "category", "url", "from", "to", "source", "verified")


def load(path: Path) -> list[SeasonalPick]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a list of seasonal picks")
    return [_pick(entry, index) for index, entry in enumerate(raw)]


def _pick(entry, index: int) -> SeasonalPick:
    if not isinstance(entry, dict):
        raise ValueError(f"seasonal pick #{index}: expected a mapping")
    ident = entry.get("id", f"#{index}")
    missing = [key for key in _REQUIRED if not entry.get(key)]
    if missing:
        raise ValueError(f"seasonal pick {ident}: missing {', '.join(missing)}")
    if entry["region"] not in REGIONS or entry["category"] not in CATEGORIES:
        raise ValueError(f"seasonal pick {ident}: bad region or category")
    for key in ("from", "to"):
        if not _MONTH_DAY.match(str(entry[key])):
            raise ValueError(f"seasonal pick {ident}: {key} must be MM-DD")
        month, day = (int(part) for part in str(entry[key]).split("-"))
        try:
            date(2000, month, day)  # 2000 is a leap year, so 02-29 stays valid
        except ValueError:
            raise ValueError(f"seasonal pick {ident}: {key} must be a real date") from None
    if safe_url(entry["url"]) is None or safe_url(entry["source"]) is None:
        raise ValueError(f"seasonal pick {ident}: url and source must be http(s)")
    match = entry.get("match") or []
    if not isinstance(match, list):
        raise ValueError(f"seasonal pick {ident}: match must be a list")
    free = entry.get("free")
    return SeasonalPick(
        id=str(entry["id"]), title=str(entry["title"]), summary=str(entry["summary"]), place=str(entry["place"]),
        city=str(entry["city"]), region=entry["region"], category=entry["category"], url=entry["url"],
        start_md=str(entry["from"]), end_md=str(entry["to"]), free=free if isinstance(free, bool) else None,
        source=entry["source"], verified=str(entry["verified"]),
        match=tuple(normalize_title(str(name)) for name in match),
    )


def _contains(month_day: str, start: str, end: str) -> bool:
    return start <= month_day <= end if start <= end else (month_day >= start or month_day <= end)


def shown(picks: list[SeasonalPick], today: date, lookahead_days: int = NEAR_DAYS) -> list[SeasonalPick]:
    """The picks in season today or opening within two weeks, the ones ending soonest first."""
    month_day = today.strftime("%m-%d")
    soon = [pick for pick in picks if _contains(month_day, pick.start_md, pick.end_md)
            or (opens(pick, today) - today).days <= lookahead_days]
    return sorted(soon, key=lambda pick: until(pick, today))


def absorb(feed: list[Event], picks: list[SeasonalPick]) -> list[Event]:
    """Drop feed listings of a seasonal pick: its title or a match, in its region, inside its window."""
    return [event for event in feed if not any(_lists(event, pick) for pick in picks)]


def _lists(event: Event, pick: SeasonalPick) -> bool:
    if event.region not in (None, pick.region) or not title_mentions(event.title, (normalize_title(pick.title),
                                                                                    *pick.match)):
        return False
    return _contains(event.start.strftime("%m-%d"), pick.start_md, pick.end_md)


def until(pick: SeasonalPick, today: date) -> date:
    """The last day of the pick's current or next window, as a real date."""
    year = today.year if pick.end_md >= today.strftime("%m-%d") else today.year + 1
    return _real_date(year, pick.end_md)


def opens(pick: SeasonalPick, today: date) -> date:
    """The first day of the pick's current or next window, as a real date."""
    end = until(pick, today)
    return _real_date(end.year if pick.start_md <= pick.end_md else end.year - 1, pick.start_md)


def _real_date(year: int, month_day: str) -> date:
    month, day = (int(part) for part in month_day.split("-"))
    try:
        return date(year, month, day)
    except ValueError:  # 02-29 outside a leap year
        return date(year, month, 28)
