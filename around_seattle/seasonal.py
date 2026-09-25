"""Curated seasonal picks from _data/around_seattle/seasonal.yml."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml

from .models import CATEGORIES, REGIONS, SeasonalPick
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
    if safe_url(entry["url"]) is None or safe_url(entry["source"]) is None:
        raise ValueError(f"seasonal pick {ident}: url and source must be http(s)")
    free = entry.get("free")
    return SeasonalPick(
        id=str(entry["id"]), title=str(entry["title"]), summary=str(entry["summary"]), place=str(entry["place"]),
        city=str(entry["city"]), region=entry["region"], category=entry["category"], url=entry["url"],
        start_md=str(entry["from"]), end_md=str(entry["to"]), free=free if isinstance(free, bool) else None,
        source=entry["source"], verified=str(entry["verified"]),
    )


def _contains(month_day: str, start: str, end: str) -> bool:
    return start <= month_day <= end if start <= end else (month_day >= start or month_day <= end)


def active(picks: list[SeasonalPick], today: date) -> list[SeasonalPick]:
    month_day = today.strftime("%m-%d")
    return [pick for pick in picks if _contains(month_day, pick.start_md, pick.end_md)]


def until(pick: SeasonalPick, today: date) -> date:
    """The last day of the pick's current window, as a real date."""
    month, day = (int(part) for part in pick.end_md.split("-"))
    year = today.year if pick.end_md >= today.strftime("%m-%d") else today.year + 1
    try:
        return date(year, month, day)
    except ValueError:  # 02-29 outside a leap year
        return date(year, month, 28)
