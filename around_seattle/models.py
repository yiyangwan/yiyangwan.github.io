"""Immutable records passed between pipeline stages, plus window helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

LA = ZoneInfo("America/Los_Angeles")

CATEGORIES = ("festival", "music", "market", "outdoors", "arts", "other")
PRIORITY_CATEGORIES = ("festival", "music", "market", "outdoors")
REGIONS = ("seattle", "eastside")

NEAR_DAYS = 14
FAR_DAYS = 60
ONGOING_AFTER_DAYS = 4
DEFAULT_TIMED_DURATION = timedelta(hours=2)


class SourceError(Exception):
    """A source could not be read; str(err) is a short reason that is safe to publish."""


class SourceSkipped(Exception):
    """A source is intentionally inactive (for example, its API key is not configured)."""


@dataclass(frozen=True)
class Window:
    now: datetime  # aware, America/Los_Angeles
    today: date
    near_end: date
    far_end: date

    @classmethod
    def starting(cls, now: datetime) -> "Window":
        local = now.astimezone(LA)
        today = local.date()
        return cls(now=local, today=today, near_end=today + timedelta(days=NEAR_DAYS),
                   far_end=today + timedelta(days=FAR_DAYS))


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    homepage: str
    type: str
    url: str
    region: str | None
    weight: int
    exclude_categories: tuple[str, ...] = ()
    require_category: bool = False
    max_pages: int = 6
    min_interval_seconds: float = 0.0
    respect_robots: bool = True
    secret_env: str | None = None


@dataclass(frozen=True)
class Event:
    source_id: str
    uid: str
    title: str
    start: datetime
    end: datetime | None
    all_day: bool
    venue: str | None = None
    location_text: str | None = None
    city: str | None = None
    region: str | None = None
    url: str | None = None
    summary: str | None = None
    price: str | None = None
    free: bool | None = None
    raw_categories: tuple[str, ...] = ()
    category: str = "other"
    score: int = 0
    more_dates: tuple[datetime, ...] = ()
    ongoing: bool = False


@dataclass(frozen=True)
class SourceResult:
    config: SourceConfig
    status: str  # "ok", "error", or "skipped"
    events: tuple[Event, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class SeasonalPick:
    id: str
    title: str
    summary: str
    place: str
    city: str
    region: str
    category: str
    url: str
    start_md: str  # "MM-DD"
    end_md: str  # "MM-DD"; earlier than start_md when the window wraps the new year
    free: bool | None
    source: str
    verified: str


def effective_end(event: Event) -> datetime:
    """End used for 'has it ended?' checks when a feed gives no end time."""
    if event.end is not None:
        return event.end
    if event.all_day:
        return datetime.combine(event.start.date() + timedelta(days=1), time(0), tzinfo=LA)
    return event.start + DEFAULT_TIMED_DURATION


def in_window(event: Event, window: Window) -> bool:
    return effective_end(event) > window.now and event.start.date() <= window.far_end


def span_days(event: Event) -> int:
    """Number of calendar days the event touches (an end at midnight does not count that day)."""
    last = (effective_end(event) - timedelta(microseconds=1)).date()
    return (last - event.start.date()).days + 1


def is_ongoing(event: Event) -> bool:
    return span_days(event) > ONGOING_AFTER_DAYS
