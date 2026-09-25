# Around Seattle data pipeline

This folder builds the data behind <https://yiyangwan.github.io/around-seattle/>.

## How it works

1. `.github/workflows/around-seattle.yml` runs every morning at 13:17 UTC (06:17 PDT, 05:17 PST), on manual
   dispatch, and when this folder, `_data/around_seattle/`, or the workflow changes on `main`.
2. The `build` job has a read-only token. It runs the tests, then `python -m around_seattle.build`, which fetches
   each calendar in `_data/around_seattle/sources.yml`, drops noise (meetings, classes, storytimes), keeps Seattle
   and Eastside events, merges duplicates, collapses repeats, scores each event, and adds the NWS forecast, sunset
   times, and the active picks from `_data/around_seattle/seasonal.yml`.
3. A separate `publish` job, the only one allowed to push, takes the file from `build`, checks it, and runs
   `publish.sh`, which commits `around-seattle.json` to the `around-seattle-data` branch. It never commits to `main`.
4. The page (`_pages/around-seattle.html`, `assets/js/around-seattle/`) fetches that file from
   raw.githubusercontent.com, with jsDelivr as a fallback, and renders it in the browser.

One failing calendar never stops the run; the page footer names it. If every calendar fails, nothing is published
and yesterday's data stays up.

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
iCal), `tribe` (WordPress The Events Calendar REST API), `civicplus` (CivicPlus calendar RSS), or
`ticketmaster`. Check the site's robots.txt and terms first, add a fixture and tests for anything new, and use
`exclude_categories` for a source's own noise categories.

## Seasonal picks

`_data/around_seattle/seasonal.yml` holds curated seasonal suggestions. Each entry names an official `source` and
the date it was `verified`. They are public factual claims on the owner's site, so review them once a year and
remove anything the source no longer supports.

## Ticketmaster (optional)

Register a free key at <https://developer.ticketmaster.com/> and add it as the repository secret
`TICKETMASTER_API_KEY` (Settings, Secrets and variables, Actions). Until then the source reports `skipped`.

## When the page says the data is stale

GitHub disables scheduled workflows in public repositories after 60 days without activity. The workflow tries to
keep itself enabled, but if the page shows the stale notice, open the repository's Actions tab, select
"Around Seattle data", enable it if needed, and run it with "Run workflow".
