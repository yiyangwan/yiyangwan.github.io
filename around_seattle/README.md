# Around Seattle data pipeline

This folder builds the data behind <https://yiyangwan.github.io/around-seattle/>.

## How it works

1. `.github/workflows/around-seattle.yml` runs every morning at 13:17 UTC (06:17 PDT, 05:17 PST), on manual
   dispatch, and when this folder, `_data/around_seattle/`, or the workflow changes on `main`.
2. The `build` job has a read-only token. It runs the tests, then `python -m around_seattle.build`, which fetches
   each calendar in `_data/around_seattle/sources.yml`, drops noise (meetings, classes, bar nights, venue tours),
   keeps Seattle and Eastside events, merges duplicates, collapses repeats, and scores each event. Only events at or
   above the listing floor are published. The build then adds the dated signature events from
   `_data/around_seattle/signature.yml`, the NWS forecast, sunset times, and the active picks from
   `_data/around_seattle/seasonal.yml`.
3. A separate `publish` job, the only one allowed to push, takes the file from `build`, checks it, and runs
   `publish.sh`, which commits `around-seattle.json` to the `around-seattle-data` branch. It never commits to `main`.
4. The page (`_pages/around-seattle.html`, `assets/js/around-seattle/`) fetches that file from
   raw.githubusercontent.com, with jsDelivr as a fallback, and renders it in the browser.

One failing calendar never stops the run; the page footer names it. If every calendar fails, nothing is published
and yesterday's data stays up.

## What the page shows

The page is a short list of what is worth going out for, not every listing in the area:

- Don't miss: the signature events of the next two weeks and the seasonal picks in season or opening within two
  weeks. Dated events come first; then the runs of more than a week and the seasonal picks, the ones ending soonest
  first.
- Today, This weekend, and Coming up: the best of the calendars for each day of the next two weeks.
- Running now: listings that run for more than four days and have already started.
- Further ahead: signature events after the next two weeks, and the few highest-scoring listings of the priority
  types (festivals, music and stage, markets and food, outdoors).

An event's score is its source's `weight`, plus its type, plus bonuses for weekends, two- to four-day runs, free
entry, and "annual" in the title, minus a penalty for a weekly series. Within two weeks an event needs `near.min_score`
to be published at all; further out it needs `further_ahead.min_score`, and at most `further_ahead.max_events` are
kept. Signature events are always published.

## Run locally

Python 3.12 or newer is required.

```bash
python3.12 -m venv /tmp/around-venv
/tmp/around-venv/bin/python -m pip install -r around_seattle/requirements.txt -r around_seattle/requirements-dev.txt
/tmp/around-venv/bin/python -m pytest around_seattle --cov=around_seattle --cov-config=around_seattle/.coveragerc
node --test around_seattle/js_tests/*.test.mjs
/tmp/around-venv/bin/python -m around_seattle.build --out /tmp/around-seattle.json
/tmp/around-venv/bin/python -m around_seattle.preview --data /tmp/around-seattle.json --out /tmp/around-preview
```

The preview builds the site with the dev config, serves it on `localhost:4000`, and saves phone and desktop
screenshots for the normal, no-weather, stale, empty, and error states. The page accepts a `?data=` override
only on `localhost` and `127.0.0.1`.

## Add or change a source

Add an entry to `_data/around_seattle/sources.yml` with one of the supported `type` values: `ics` (Trumba
iCal), `tribe` (WordPress The Events Calendar REST API), `civicplus` (CivicPlus calendar RSS), or `ticketmaster`.
Check the site's robots.txt and terms first, and add a fixture and tests for anything new. The client checks robots.txt
on every request, query string included, so a source whose rules forbid its feed URL fails as "robots.txt
disallows". Prefer calendars that are curated at the source, such as a venue's or organizer's own programs.

Per source, `exclude_categories` drops a source's own noise categories, and `include_categories` keeps only the
listed ones. `day_cap` keeps a busy source from taking every slot: past that many events on a day, the rest fall below
the listing floor. For Ticketmaster, `arena_venues` and `major_venues` name the venues whose shows are kept (arena
shows rank higher), and `midsize_venues` names the venues whose shows are kept only for acts with a Wikipedia page.
Every other venue's shows are left out.

## Signature events

`_data/around_seattle/signature.yml` lists the annual festivals, celebrations, and holiday traditions worth planning
around, many of which no calendar feed carries. Each entry has a one-sentence summary and dated ranges, and each date
range names the official page that states it (`source`) and the day it was checked (`verified`). These are public
factual claims on the owner's site: copy dates only from the official page, and never guess a year's dates from the
year before.

An entry with no upcoming dates shows nothing. The build log names such entries ("signature: 2 entries need their
next dates (...)"), and `usually` says when each one normally happens, so the next dates can be added once they are
announced. `match` lists feed titles for the same event, so a feed's own listing of it is dropped in favor of the
entry.

## Seasonal picks

`_data/around_seattle/seasonal.yml` holds curated seasonal sights, such as salmon runs and fall color, shown under
Don't miss while today falls inside their window. Each entry names an official `source` and the date it was
`verified`. They are public factual claims on the owner's site, so review them once a year and remove anything the
source no longer supports. As with signature events, `match` lists feed titles for the same sight, so a feed's
listing of it is dropped in favor of the pick while it is in season.

## Ticketmaster (optional)

Register a free key at <https://developer.ticketmaster.com/> and add it as the repository secret
`TICKETMASTER_API_KEY` (Settings, Secrets and variables, Actions). Until then the source reports `skipped`.

## When the page says the data is stale

GitHub disables scheduled workflows in public repositories after 60 days without activity. The workflow tries to
keep itself enabled, but if the page shows the stale notice, open the repository's Actions tab, select
"Around Seattle data", enable it if needed, and run it with "Run workflow".
