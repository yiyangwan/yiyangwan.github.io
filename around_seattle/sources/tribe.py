"""WordPress "The Events Calendar" REST API (Town Hall Seattle, Experience Redmond)."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..models import LA, Event, SourceConfig, SourceError, Window, in_window
from ..text import clean_inline, html_to_text, parse_price, safe_url, scrub_contacts, tidy_summary, truncate

PER_PAGE = 50
LOCAL_FORMAT = "%Y-%m-%d %H:%M:%S"


def collect(config: SourceConfig, http, window: Window) -> list[Event]:
    events: list[Event] = []
    saw_items = False
    for page in range(1, config.max_pages + 1):
        params = {"start_date": window.today.isoformat(), "end_date": window.far_end.isoformat(),
                  "per_page": PER_PAGE, "page": page}
        data = http.get_json(config.url, params, min_interval=config.min_interval_seconds,
                             respect_robots=config.respect_robots)
        items = data.get("events") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise SourceError("unexpected response")
        saw_items = saw_items or bool(items)
        events.extend(event for event in (_safe_event(item, config) for item in items) if event is not None)
        if page >= _page_count(data.get("total_pages")):
            break
    if saw_items and not events:
        raise SourceError("could not parse any items")
    return [event for event in events if in_window(event, window)]


def _page_count(value) -> int:
    """The feed's page count, or 0 (stop after this page) when it is not a number."""
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return 0


def _safe_event(item, config: SourceConfig) -> Event | None:
    """to_event for one item; a malformed item is skipped instead of failing the whole source."""
    try:
        return to_event(item, config)
    except (TypeError, ValueError, AttributeError, KeyError, OverflowError):
        return None


def _zone(name) -> ZoneInfo:
    try:
        return ZoneInfo(name) if name else LA
    except (ZoneInfoNotFoundError, ValueError, TypeError, OSError):
        return LA


def _local(value, zone) -> datetime | None:
    try:
        return datetime.strptime(str(value), LOCAL_FORMAT).replace(tzinfo=zone).astimezone(LA)
    except ValueError:
        return None


def to_event(item, config: SourceConfig) -> Event | None:
    if not isinstance(item, dict) or item.get("hide_from_listings") or item.get("status", "publish") != "publish":
        return None
    title = clean_inline(item.get("title"))
    zone = _zone(item.get("timezone"))
    start = _local(item.get("start_date"), zone)
    end = _local(item.get("end_date"), zone)
    if not title or start is None:
        return None
    all_day = bool(item.get("all_day"))
    if all_day:
        last_day = (end or start).date()
        start = datetime.combine(start.date(), time(0), tzinfo=LA)
        end = datetime.combine(last_day + timedelta(days=1), time(0), tzinfo=LA)
    elif end is not None and end <= start:
        end = None
    venue = item.get("venue") if isinstance(item.get("venue"), dict) else {}
    venue_name = clean_inline(venue.get("venue")) or None
    if item.get("is_virtual") and not venue_name:
        return None
    city = clean_inline(venue.get("city")) or None
    address = ", ".join(part for part in (
        venue_name, clean_inline(venue.get("address")), city, clean_inline(venue.get("state") or venue.get("province")),
    ) if part)
    price, free = parse_price(item.get("cost"))
    categories = tuple(name for name in (clean_inline(c.get("name")) for c in item.get("categories") or []
                                         if isinstance(c, dict)) if name)
    description = html_to_text(item.get("excerpt")) or html_to_text(item.get("description"))
    return Event(
        source_id=config.id,
        uid=f"{config.id}:{item.get('id')}",
        title=title,
        start=start,
        end=end,
        all_day=all_day,
        venue=venue_name,
        location_text=address or None,
        city=city,
        url=safe_url(item.get("url")),
        summary=truncate(tidy_summary(scrub_contacts(" ".join(description.splitlines())))) or None,
        price=price,
        free=free,
        raw_categories=categories,
    )
