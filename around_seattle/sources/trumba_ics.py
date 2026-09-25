"""Trumba iCal feeds (seattle.gov city-wide calendar, UW Seattle campus calendar)."""
from __future__ import annotations

from datetime import date, datetime, time

from icalendar import Calendar

from ..models import LA, Event, SourceConfig, SourceError, Window, in_window
from ..text import clean_inline, html_to_text, join_lines, parse_price, safe_url, scrub_contacts, tidy_summary, truncate

# Custom fields that describe the event type. "Parks Event Category" is the same boilerplate on
# almost every Parks event, so it is ignored.
TYPE_FIELDS = ("Event Types", "Location Type")
# DESCRIPTION repeats the custom fields as "Name: value" lines; these labels are metadata too.
EXTRA_META_LABELS = frozenset({
    "link", "contact", "contact phone", "contact email", "registration details", "site contact details",
    "pre-register", "cost", "audience", "neighborhoods", "agendas",
})


def collect(config: SourceConfig, http, window: Window) -> list[Event]:
    text = http.get_text(config.url, min_interval=config.min_interval_seconds, respect_robots=config.respect_robots)
    return [event for event in parse(text, config) if in_window(event, window)]


def parse(text: str, config: SourceConfig) -> list[Event]:
    try:
        calendar = Calendar.from_ical(text)
    except ValueError as exc:
        raise SourceError("invalid iCal") from exc
    events = (_to_event(component, config) for component in calendar.walk("VEVENT"))
    return [event for event in events if event is not None]


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _to_la(value) -> tuple[datetime, bool]:
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=LA)
        return aware.astimezone(LA), False
    if isinstance(value, date):
        return datetime.combine(value, time(0), tzinfo=LA), True
    raise TypeError(f"unsupported date value {value!r}")


def _custom_fields(component) -> dict[str, str]:
    fields = {}
    for prop in _as_list(component.get("X-TRUMBA-CUSTOMFIELD")):
        name = prop.params.get("NAME")
        if name:
            fields[str(name)] = str(prop).replace("\\,", ",").replace("\\;", ";")
    return fields


def _categories(component) -> list[str]:
    names = []
    for prop in _as_list(component.get("CATEGORIES")):
        values = getattr(prop, "cats", None)
        names.extend(clean_inline(value) for value in (values if values is not None else str(prop).split(",")))
    return [name for name in names if name]


def _summary(description: str, field_names) -> str | None:
    labels = {name.casefold() for name in field_names} | EXTRA_META_LABELS
    kept = []
    for line in html_to_text(description).splitlines():
        label, separator, _ = line.partition(":")
        if separator and label.strip().casefold() in labels:
            continue
        kept.append(line)
    return truncate(tidy_summary(scrub_contacts(" ".join(kept)))) or None


def _to_event(component, config: SourceConfig) -> Event | None:
    title = clean_inline(str(component.get("SUMMARY", "")))
    start_prop = component.get("DTSTART")
    if not title or start_prop is None:
        return None
    try:
        start, all_day = _to_la(start_prop.dt)
        end_prop = component.get("DTEND")
        end = _to_la(end_prop.dt)[0] if end_prop is not None else None
    except (TypeError, ValueError):
        return None
    if end is not None and end <= start:
        end = None
    fields = _custom_fields(component)
    raw_categories = _categories(component)
    for name in TYPE_FIELDS:
        raw_categories.extend(part for part in (clean_inline(v) for v in fields.get(name, "").split(",")) if part)
    location = join_lines(str(component.get("LOCATION", ""))) or None
    price, free = parse_price(fields.get("Cost"))
    url = safe_url(str(component.get("X-TRUMBA-LINK", ""))) or safe_url(str(component.get("URL", "")))
    return Event(
        source_id=config.id,
        uid=str(component.get("UID", "")) or f"{title}|{start.isoformat()}",
        title=title,
        start=start,
        end=end,
        all_day=all_day,
        venue=location.split(", ")[0] if location else None,
        location_text=location,
        url=url,
        summary=_summary(str(component.get("DESCRIPTION", "")), fields),
        price=price,
        free=free,
        raw_categories=tuple(dict.fromkeys(raw_categories)),
    )
