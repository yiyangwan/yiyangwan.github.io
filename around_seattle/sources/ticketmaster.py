"""Ticketmaster Discovery API v2. Dormant until the TICKETMASTER_API_KEY secret is set."""
from __future__ import annotations

import os
import re
from datetime import datetime, time, timedelta, timezone

from ..models import LA, Event, SourceConfig, SourceError, SourceSkipped, Window, in_window
from ..text import clean_inline, safe_url

SEATTLE_TACOMA_DMA = 385
PAGE_SIZE = 200
KEPT_SEGMENTS = frozenset({"music", "arts & theatre", "miscellaneous", "film"})
DROPPED_STATUSES = frozenset({"cancelled", "canceled", "postponed"})
# Ticketmaster lists parking and upsells as their own "events".
ADD_ON = re.compile(r"\b(?:parking|vip|suites?|premium seating|platinum|upgrades?|gift cards?|packages?)\b",
                    re.IGNORECASE)
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def collect(config: SourceConfig, http, window: Window, env=None) -> list[Event]:
    key = (os.environ if env is None else env).get(config.secret_env or "", "")
    if not key:
        raise SourceSkipped("no API key configured")
    start = datetime.combine(window.today, time(0), tzinfo=LA).astimezone(timezone.utc)
    end = datetime.combine(window.far_end + timedelta(days=1), time(0), tzinfo=LA).astimezone(timezone.utc)
    events: list[Event] = []
    for page in range(config.max_pages):
        params = {"apikey": key, "dmaId": SEATTLE_TACOMA_DMA, "size": PAGE_SIZE, "page": page, "sort": "date,asc",
                  "startDateTime": start.strftime(UTC_FORMAT), "endDateTime": end.strftime(UTC_FORMAT)}
        data = http.get_json(config.url, params, min_interval=config.min_interval_seconds,
                             respect_robots=config.respect_robots)
        if not isinstance(data, dict):
            raise SourceError("unexpected response")
        items = (data.get("_embedded") or {}).get("events") or []
        events.extend(event for event in (_safe_event(item, config) for item in items) if event is not None)
        if page + 1 >= _page_count((data.get("page") or {}).get("totalPages")):
            break
    return [event for event in events if in_window(event, window)]


def _page_count(value) -> int:
    """The response's page count, or 0 (stop after this page) when it is not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _safe_event(item, config: SourceConfig) -> Event | None:
    """to_event for one item; a malformed item is skipped instead of failing the whole source."""
    try:
        return to_event(item, config)
    except (TypeError, ValueError, AttributeError, KeyError):
        return None


def _start(info: dict) -> tuple[datetime | None, bool]:
    local_date = info.get("localDate")
    if not local_date:
        return None, False
    try:
        day = datetime.strptime(local_date, "%Y-%m-%d").date()
        if info.get("noSpecificTime") or info.get("timeTBA") or not info.get("localTime"):
            return datetime.combine(day, time(0), tzinfo=LA), True
        return datetime.combine(day, datetime.strptime(info["localTime"], "%H:%M:%S").time(), tzinfo=LA), False
    except ValueError:
        return None, False


def _price(ranges) -> str | None:
    for entry in ranges or []:
        low, high = entry.get("min"), entry.get("max")
        if entry.get("currency", "USD") == "USD" and isinstance(low, (int, float)) and isinstance(high, (int, float)):
            return f"${low:,.0f}" if low == high else f"${low:,.0f} to ${high:,.0f}"
    return None


def to_event(item, config: SourceConfig) -> Event | None:
    if not isinstance(item, dict):
        return None
    title = clean_inline(item.get("name"))
    if not title or ADD_ON.search(title):
        return None
    dates = item.get("dates") or {}
    if str((dates.get("status") or {}).get("code", "")).casefold() in DROPPED_STATUSES:
        return None
    classification = next(iter(item.get("classifications") or []), None) or {}
    segment = clean_inline((classification.get("segment") or {}).get("name"))
    if segment.casefold() not in KEPT_SEGMENTS:
        return None
    start, all_day = _start(dates.get("start") or {})
    if start is None:
        return None
    venue = next(iter((item.get("_embedded") or {}).get("venues") or []), None) or {}
    venue_name = clean_inline(venue.get("name")) or None
    city = clean_inline((venue.get("city") or {}).get("name")) or None
    address = clean_inline((venue.get("address") or {}).get("line1"))
    state = clean_inline((venue.get("state") or {}).get("stateCode"))
    genres = [clean_inline((classification.get(key) or {}).get("name")) for key in ("genre", "subGenre")]
    return Event(
        source_id=config.id,
        uid=f"{config.id}:{item.get('id')}",
        title=title,
        start=start,
        end=datetime.combine(start.date() + timedelta(days=1), time(0), tzinfo=LA) if all_day else None,
        all_day=all_day,
        venue=venue_name,
        location_text=", ".join(part for part in (venue_name, address, city, state) if part) or None,
        city=city,
        url=safe_url(item.get("url")),
        price=_price(item.get("priceRanges")),
        raw_categories=tuple(name for name in (segment, *genres) if name and name.casefold() != "undefined"),
    )
