# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## HARD RULE: never change information beyond the ask

**Never update any information beyond what the owner explicitly asked for.** Not a preference — a hard rule, and it outranks every other instruction in this file.

This repo is the owner's public academic identity and CV. Every line is a factual claim they personally stand behind in hiring, immigration, and academic contexts. An unauthorized edit misstates their record publicly without their knowledge, and costs them the ability to trust the repo without re-auditing it line by line.

- Scope each edit to the exact file, field, and record named in the request. Updating a talk record does **not** license editing the matching publication record — `_talks/` and `_publications/` are separate collections holding separate claims.
- If an adjacent field looks stale, wrong, or improvable while you are in there, **stop and ask.** Do not fix it in passing, do not bundle it into the same commit, and do not justify it as keeping the record consistent.
- Never add a metric that was not requested. In particular, **no citation counts, h-index, download counts, or impact factors in the CV.**
- If a requested change leaves a neighbouring field inconsistent, surface the inconsistency and let the owner decide. Do not resolve it yourself.
- Before committing, read every hunk of the diff and ask "was this one requested?" Drop any hunk where the answer is no.
- Adding a comment that explains why a value is what it is: fine. Changing the value: not without asking.

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

CV (`files/yiyangwang_cv.pdf`, the PDF `_pages/cv.md` links to) is compiled from LaTeX:

```bash
./CV/build.sh        # CV/yiyangwang_cv.tex -> files/yiyangwang_cv.pdf (in place)
```

The script backs up the previous PDF to `CV/backups/` first, then builds via `tectonic`
in a temp dir and moves the result over `files/yiyangwang_cv.pdf` — no manual copy or
rename step. `CV/` is tracked (source, class, bundled fonts, and build script), so the
build is reproducible from a fresh clone. `Keval-resume.cls` uses `fontspec` with fonts
loaded by relative path from `CV/fonts/georgia/`, so the engine must be XeLaTeX
(`tectonic`) run with `CV/` as the working directory — `pdflatex` will not work.
Prune `CV/backups/` occasionally; it grows by one PDF per build.

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
