"""CivicPlus calendar RSS (City of Redmond, City of Issaquah)."""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ..models import LA, Event, SourceConfig, SourceError, Window, in_window
from ..text import clean_inline, html_to_text, safe_url

_DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
_DATES = re.compile(rf"({_DATE})(?:\s*-\s*({_DATE}))?")
_TIME = r"\d{1,2}:\d{2}\s*[AP]M"
_TIMES = re.compile(rf"({_TIME})(?:\s*-\s*({_TIME}))?", re.IGNORECASE)


def collect(config: SourceConfig, http, window: Window) -> list[Event]:
    text = http.get_text(config.url, min_interval=config.min_interval_seconds, respect_robots=config.respect_robots)
    return [event for event in parse(text, config) if in_window(event, window)]


def parse(text: str, config: SourceConfig) -> list[Event]:
    # A byte order mark would fail the RSS check, and blank lines before the XML declaration would fail the parse.
    feed = text.lstrip("\ufeff \t\r\n")
    head = feed[:200].lower()
    if not (head.startswith("<?xml") or head.startswith("<rss")):
        raise SourceError("not an RSS feed")  # typically a bot-challenge HTML page
    try:
        root = ElementTree.fromstring(feed)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise SourceError("invalid RSS") from exc
    items = list(root.iter("item"))
    events = []
    for item in items:
        # Namespace URIs differ per city, so match child elements by local name.
        fields = {child.tag.rsplit("}", 1)[-1]: (child.text or "").strip() for child in item}
        event = _to_event(fields, config)
        if event is not None:
            events.append(event)
    if items and not events:  # a feed whose format changed would otherwise look healthy and empty
        raise SourceError("could not parse any items")
    return events


def _parse_date(value: str):
    return datetime.strptime(value, "%B %d, %Y").date()


def _parse_time(value: str):
    return datetime.strptime(" ".join(value.upper().split()), "%I:%M %p").time()


def _location(description: str, fallback: str) -> str | None:
    lines = html_to_text(description).splitlines()
    for index, line in enumerate(lines):
        label, separator, rest = line.partition(":")
        if separator and label.strip().casefold() == "location":
            joined = ", ".join(part for part in [rest.strip(), *lines[index + 1:]] if part)
            if joined:
                return joined
    return clean_inline(fallback) or None


def _to_event(fields: dict[str, str], config: SourceConfig) -> Event | None:
    title = clean_inline(fields.get("title"))
    dates = _DATES.search(fields.get("EventDates", ""))
    if not title or not dates:
        return None
    try:
        first_day = _parse_date(dates.group(1))
        last_day = _parse_date(dates.group(2)) if dates.group(2) else first_day
        times = _TIMES.search(fields.get("EventTimes", ""))
        if times:
            start = datetime.combine(first_day, _parse_time(times.group(1)), tzinfo=LA)
            end = datetime.combine(last_day, _parse_time(times.group(2)), tzinfo=LA) if times.group(2) else None
            if end is not None and end <= start:
                end += timedelta(days=1)
            all_day = False
        else:
            start = datetime.combine(first_day, time(0), tzinfo=LA)
            end = datetime.combine(last_day + timedelta(days=1), time(0), tzinfo=LA)
            all_day = True
    except ValueError:
        return None
    location = _location(fields.get("description", ""), fields.get("Location", ""))
    link = safe_url(fields.get("link"))
    return Event(
        source_id=config.id,
        uid=f"{link or title}|{start.isoformat()}",
        title=title,
        start=start,
        end=end,
        all_day=all_day,
        venue=location.split(", ")[0] if location else None,
        location_text=location,
        url=link,
    )
