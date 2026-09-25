"""Build around-seattle.json for the /around-seattle/ page.

    python -m around_seattle.build --out PATH [--now ISO_TIMESTAMP] [--config-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import yaml

from . import classify, dedupe, regions, schema, seasonal, sun, weather
from .http import HttpClient
from .models import (LA, PRIORITY_CATEGORIES, Event, SourceConfig, SourceError, SourceResult, SourceSkipped, Window,
                     is_ongoing)
from .score import score
from .sources import civicplus, ticketmaster, tribe, trumba_ics

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = REPO_ROOT / "_data" / "around_seattle"
ADAPTERS = {
    "ics": lambda config, http, window, env: trumba_ics.collect(config, http, window),
    "tribe": lambda config, http, window, env: tribe.collect(config, http, window),
    "civicplus": lambda config, http, window, env: civicplus.collect(config, http, window),
    "ticketmaster": lambda config, http, window, env: ticketmaster.collect(config, http, window, env),
}


def load_sources(path: Path) -> tuple[list[SourceConfig], dict]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    configs = []
    for entry in raw.get("sources") or []:
        if entry.get("type") not in ADAPTERS:
            raise ValueError(f"source {entry.get('id')}: unknown type {entry.get('type')!r}")
        configs.append(SourceConfig(
            id=entry["id"], name=entry["name"], homepage=entry["homepage"], type=entry["type"], url=entry["url"],
            region=entry.get("region"), weight=int(entry["weight"]),
            exclude_categories=tuple(entry.get("exclude_categories") or ()),
            require_category=bool(entry.get("require_category", False)),
            max_pages=int(entry.get("max_pages", 6)),
            min_interval_seconds=float(entry.get("min_interval_seconds", 0)),
            respect_robots=bool(entry.get("respect_robots", True)),
            secret_env=entry.get("secret_env"),
        ))
    further = raw.get("further_ahead") or {}
    return configs, {"min_score": int(further.get("min_score", 50)), "max_events": int(further.get("max_events", 30))}


def _redact(message: str, env, names) -> str:
    for name in names:
        secret = env.get(name)
        if secret:
            message = message.replace(secret, "***")
    return message


def run_sources(configs, http, window: Window, env) -> list[SourceResult]:
    names = {c.secret_env for c in configs if c.secret_env} | {"TICKETMASTER_API_KEY"}
    results = []
    for config in configs:
        try:
            events = ADAPTERS[config.type](config, http, window, env)
            results.append(SourceResult(config, "ok", tuple(events)))
        except SourceSkipped as exc:
            results.append(SourceResult(config, "skipped", error=str(exc)))
        except SourceError as exc:
            results.append(SourceResult(config, "error", error=_redact(str(exc), env, names)))
        except Exception as exc:  # a bug in one adapter must not stop the others
            print(_redact(f"{config.id}: {type(exc).__name__}: {exc}", env, names), file=sys.stderr)
            results.append(SourceResult(config, "error", error=type(exc).__name__))
    return results


def select(events: list[Event], window: Window, further: dict) -> list[Event]:
    near = [e for e in events if e.start.date() <= window.near_end]
    far = [e for e in events if e.start.date() > window.near_end and e.category in PRIORITY_CATEGORIES
           and e.score >= further["min_score"]]
    far = sorted(far, key=lambda e: (-e.score, e.start))[: further["max_events"]]
    return sorted(near + far, key=lambda e: (e.start, -e.score, e.title))


def process(results, configs, window: Window, further: dict) -> list[Event]:
    by_id = {config.id: config for config in configs}
    weights = {config.id: config.weight for config in configs}
    kept = []
    for result in results:
        config = by_id[result.config.id]
        for event in result.events:
            if classify.is_noise(event, config):
                continue
            placed = regions.assign_region(event, config.region)
            if placed is None:
                continue
            typed = replace(placed, category=classify.categorize(placed))
            if config.require_category and typed.category == "other":
                continue
            kept.append(typed)
    collapsed = dedupe.collapse_recurring(dedupe.merge_duplicates(kept, weights))
    scored = [replace(e, ongoing=is_ongoing(e), score=score(e, weights[e.source_id])) for e in collapsed]
    return select(scored, window, further)


def main(argv=None, *, http=None, env=None) -> int:
    parser = argparse.ArgumentParser(description="Build around-seattle.json for the /around-seattle/ page.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--now", help="ISO 8601 timestamp to build as of (default: now)")
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(LA)
    now = now if now.tzinfo else now.replace(tzinfo=LA)
    window = Window.starting(now)
    configs, further = load_sources(args.config_dir / "sources.yml")
    picks = seasonal.load(args.config_dir / "seasonal.yml")
    client = http if http is not None else HttpClient()

    results = run_sources(configs, client, window, env)
    for result in results:
        detail = f" ({result.error})" if result.error else ""
        print(f"{result.config.id}: {result.status}, {len(result.events)} events{detail}")
    if not any(result.status == "ok" for result in results):
        print("error: every event source failed; nothing written", file=sys.stderr)
        return 2

    events = process(results, configs, window, further)
    if not events:
        # Feeds that answer but leave nothing to show mean a silent breakage somewhere. An empty page is never right
        # for sixty days of these calendars, so keep yesterday's data up instead.
        print("error: no events after filtering; nothing written", file=sys.stderr)
        return 2
    try:
        weather_data = weather.collect(client)
    except Exception as exc:  # a weather outage must not stop the rest of the build
        weather_data = None
        print(f"weather: error ({type(exc).__name__})")
    else:
        print(f"weather: ok ({', '.join(weather_data)})" if weather_data else "weather: unavailable")
    output = schema.to_output(generated_at=now, window=window, results=results, events=events,
                              weather=weather_data, sun=sun.for_window(window),
                              seasonal=seasonal.active(picks, window.today))
    try:
        schema.validate(output)
    except schema.SchemaError as exc:
        print(f"error: invalid output: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_name(args.out.name + ".tmp")
    temporary.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(temporary, args.out)
    print(f"wrote {len(events)} events to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
