"""Output serialization (camelCase JSON, schema version 1) and invariant checks."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from . import seasonal as seasonal_picks
from .dedupe import MAX_MORE_DATES
from .models import CATEGORIES, REGIONS, Event, SeasonalPick, SourceResult, Window, effective_end
from .text import safe_url
from .weather import SEVERITY

SCHEMA_VERSION = 1
STATUSES = ("ok", "error", "skipped")
EVENT_KEYS = frozenset({"id", "title", "start", "end", "allDay", "venue", "city", "region", "category", "free",
                        "price", "url", "summary", "source", "score", "moreDates", "ongoing"})


class SchemaError(ValueError):
    """The output breaks a documented invariant."""


def event_id(event: Event) -> str:
    key = f"{event.source_id}|{event.uid}|{event.start.isoformat()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def _event(event: Event) -> dict:
    # An all-day event with no explicit end still needs one: the page must never compute it
    # itself, because that goes wrong on DST days. A timed event with no end stays null.
    end = effective_end(event) if event.all_day and event.end is None else event.end
    return {
        "id": event_id(event), "title": event.title, "start": event.start.isoformat(),
        "end": end.isoformat() if end else None, "allDay": event.all_day,
        "venue": event.venue, "city": event.city, "region": event.region, "category": event.category,
        "free": event.free, "price": event.price, "url": event.url, "summary": event.summary,
        "source": event.source_id, "score": event.score,
        "moreDates": [moment.isoformat() for moment in event.more_dates[:MAX_MORE_DATES]],
        "ongoing": event.ongoing,
    }


def _source(result: SourceResult) -> dict:
    return {"id": result.config.id, "name": result.config.name, "homepage": result.config.homepage,
            "status": result.status, "count": len(result.events), "error": result.error}


def _seasonal(pick: SeasonalPick, window: Window) -> dict:
    return {"id": pick.id, "title": pick.title, "summary": pick.summary, "place": pick.place, "city": pick.city,
            "region": pick.region, "category": pick.category, "url": pick.url, "free": pick.free,
            "until": seasonal_picks.until(pick, window.today).isoformat()}


def to_output(*, generated_at: datetime, window: Window, results, events, weather, sun, seasonal) -> dict:
    stamp = generated_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": stamp,
        "timezone": "America/Los_Angeles",
        "window": {"start": window.today.isoformat(), "nearEnd": window.near_end.isoformat(),
                   "farEnd": window.far_end.isoformat()},
        "sources": [_source(result) for result in results],
        "weather": weather,
        "sun": sun,
        "seasonal": [_seasonal(pick, window) for pick in seasonal],
        "events": [_event(event) for event in events],
    }


def _iso(value, where: str) -> None:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchemaError(f"{where}: not ISO 8601") from exc


def _check_event(event: dict, where: str, seen: set) -> None:
    if set(event) != EVENT_KEYS:
        raise SchemaError(f"{where}: unexpected keys")
    if not isinstance(event["title"], str) or not event["title"]:
        raise SchemaError(f"{where}: title")
    _iso(event["start"], f"{where}.start")
    if event["end"] is not None:
        _iso(event["end"], f"{where}.end")
    if event["category"] not in CATEGORIES:
        raise SchemaError(f"{where}: category")
    if event["region"] not in REGIONS:
        raise SchemaError(f"{where}: region")
    if event["url"] is not None and safe_url(event["url"]) is None:
        raise SchemaError(f"{where}: url")
    if not isinstance(event["score"], int) or not 0 <= event["score"] <= 100:
        raise SchemaError(f"{where}: score")
    if event["free"] not in (True, False, None) or not isinstance(event["free"], (bool, type(None))):
        raise SchemaError(f"{where}: free")
    if event["id"] in seen:
        raise SchemaError(f"{where}: duplicate id")
    seen.add(event["id"])


def validate(output: dict) -> None:
    if output.get("schemaVersion") != SCHEMA_VERSION:
        raise SchemaError("schemaVersion must be 1")
    _iso(output.get("generatedAt"), "generatedAt")
    events = output.get("events")
    if not isinstance(events, list):
        raise SchemaError("events must be a list")
    seen: set = set()
    for index, event in enumerate(events):
        _check_event(event, f"events[{index}]", seen)
    for index, source in enumerate(output.get("sources") or []):
        if source.get("status") not in STATUSES:
            raise SchemaError(f"sources[{index}]: status")
    for region, forecast in (output.get("weather") or {}).items():
        if region not in REGIONS:
            raise SchemaError(f"weather.{region}: region")
        for period in (forecast or {}).get("periods", []):
            if period.get("condition") not in SEVERITY:
                raise SchemaError(f"weather.{region}: condition")
    for index, pick in enumerate(output.get("seasonal") or []):
        if safe_url(pick.get("url")) is None:
            raise SchemaError(f"seasonal[{index}]: url")
