# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jekyll-based personal academic homepage for Yiyang Wang, hosted on GitHub Pages at https://yiyangwan.github.io. Built on the academicpages template (a Minimal Mistakes derivative). Live site rebuilds automatically when `main` is pushed.

## Development Commands

```bash
# Local dev (analytics disabled, base URL = localhost:4000)
bundle exec jekyll serve --config _config.yml,_config.dev.yml

# Production-config preview
bundle exec jekyll serve

# Static build into _site/
bundle exec jekyll build
```

JavaScript bundle (`assets/js/main.min.js`) is generated via npm — only needed if editing files under `assets/js/_main.js`, `assets/js/plugins/`, or `assets/js/vendor/`:

```bash
npm install
npm run build:js     # one-shot uglify
npm run watch:js     # rebuild on change
```

## Architecture

### Collections (defined in `_config.yml`)

Four Jekyll collections with `output: true` and `permalink: /:collection/:path/`:

- `_publications/` — research papers (one md file per paper, e.g. `AGG.md`, `BANDIT.md`)
- `_talks/` — talks; uses dedicated `talk` layout (which renders the `location:` field used by talkmap)
- `_teaching/` — courses
- `_portfolio/` — portfolio items

`_posts/` is the standard Jekyll posts directory (not a collection). `_pages/` is included via the `include:` list and contains static pages plus the homepage `about.md` (`permalink: /`).

Per-collection layout defaults are configured under `defaults:` in `_config.yml` — touching `layout:` in individual files is rarely needed.

### Batch content generation

`markdown_generator/` converts TSV → markdown. Edit the TSV, then run the matching script:

- `publications.tsv` → `python publications.py` (or `publications.ipynb`)
- `talks.tsv` → `python talks.py` (or `talks.ipynb`)
- `PubsFromBib.ipynb` / `pubsFromBib.py` — generate publications from a `.bib` file

Generated files land in `_publications/` or `_talks/` and overwrite by filename — keep TSV as source of truth if using this flow.

### Talkmap

`talkmap.py` (run from `_talks/`) scrapes `location:` fields, geocodes via Nominatim, and writes a Leaflet cluster map into `talkmap/`. Surfaced through `_pages/talkmap.html`. Requires `glob`, `getorg`, `geopy`.

### Theme & layouts

`theme: jekyll-theme-merlot` is set in `_config.yml`, but actual rendering uses the local layouts in `_layouts/` (`single.html`, `talk.html`, `archive.html`, `splash.html`, `default.html`, `compress.html`). Custom partials live in `_includes/`; styles in `_sass/` (compiled with `style: compressed`).

### Configuration notes

- `_config.yml` is **not** auto-reloaded — restart `jekyll serve` after editing.
- `future: false` — posts dated in the future are skipped (see `_posts/2199-01-01-future-post.md` for the placeholder).
- `incremental: false` — full rebuild every time.
- Author profile (sidebar on every page) is centralized in the `author:` block in `_config.yml`.
- Analytics: `google-gtag` with tracking_id `G-0X16EGXERM`; disabled by `_config.dev.yml`.
- Plugins: `jekyll-paginate`, `jekyll-gist`, `jekyll-feed`, `jekyll-redirect-from`. `jekyll-sitemap` comes from the Gemfile via GitHub source. `hawkins` is available for LiveReload.

### Frontmatter conventions

Publication:
```yaml
---
title: "Paper Title"
collection: publications
permalink: /publications/SHORT-NAME
date: YYYY-MM-DD
venue: 'Venue Name'
excerpt: "<p align='center'><a href='/publications/SHORT-NAME'><img src='/images/SHORT-NAME.png' style='width: 500px;'/></a></p>"
# paperurl, citation are optional
---
```

Post (filename must be `YYYY-MM-DD-slug.md`):
```yaml
---
title: 'Post Title'
date: YYYY-MM-DD
permalink: /posts/YYYY/MM/slug/
tags: [tag1, tag2]
---
```

## Deployment

Push to `main` → GitHub Pages rebuilds via the `github-pages` gem. The site serves from the repo root (no `/docs` folder). `_site/` is gitignored and only used locally.
