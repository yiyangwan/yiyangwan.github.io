# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

<<<<<<< Updated upstream
This is a Jekyll-based personal academic website for Yiyang Wang, hosted on GitHub Pages. The site uses the Minimal Mistakes theme and is structured around Jekyll collections for organizing academic content (publications, talks, teaching, portfolio).
=======
This is a Jekyll-based personal academic homepage for Yiyang Wang (https://yiyangwan.github.io/), built using the Minimal Mistakes theme. The site showcases publications, blog posts, teaching materials, talks, and portfolio items.
>>>>>>> Stashed changes

## Development Commands

### Local Development
```bash
<<<<<<< Updated upstream
# Install Ruby dependencies
bundle install

# Serve site locally (development config)
bundle exec jekyll serve --config _config.yml,_config.dev.yml

# Serve site locally (production config)
bundle exec jekyll serve

# Build site
bundle exec jekyll build
```

### JavaScript Build
```bash
# Install Node dependencies
npm install

# Build and minify JavaScript
npm run build:js

# Watch for JavaScript changes and rebuild
npm run watch:js
```

## Architecture and Structure

### Jekyll Collections
The site uses Jekyll collections to organize different content types:
- `_publications/` - Research papers and working papers
- `_talks/` - Conference talks and presentations
- `_teaching/` - Teaching materials and courses
- `_portfolio/` - Portfolio items
- `_pages/` - Static pages (about, CV, contact, etc.)
- `_posts/` - Blog posts (if used)

Each collection item is a markdown file with YAML frontmatter defining metadata like title, date, venue, and permalink.

### Content Generation with Markdown Generator
The `markdown_generator/` directory contains Jupyter notebooks and Python scripts for batch-generating markdown files from TSV data:
- `publications.tsv` / `publications.py` / `publications.ipynb` - Generate publication pages
- `talks.tsv` / `talks.py` / `talks.ipynb` - Generate talk pages
- `PubsFromBib.ipynb` / `pubsFromBib.py` - Generate publications from BibTeX

Use these tools when adding multiple publications or talks at once. Edit the TSV files, then run the corresponding notebook or Python script to generate markdown files.

### Configuration Files
- `_config.yml` - Main Jekyll configuration (author info, collections, plugins, theme settings)
- `_config.dev.yml` - Development overrides (can be merged with main config)
- `Gemfile` - Ruby dependencies (Jekyll, github-pages gem, plugins)
- `package.json` - Node dependencies for JavaScript build

### Key Directories
- `_data/` - YAML/JSON data files used across the site
- `_includes/` - Reusable HTML/Liquid template components
- `_layouts/` - Page layout templates
- `_sass/` - Sass stylesheets
- `assets/` - Static assets (CSS, JS, images)
- `files/` - Downloadable files (e.g., CV PDF)
- `images/` - Image files for content

## Content Management

### Adding a New Publication
1. Create a new markdown file in `_publications/` with filename like `SHORT-NAME.md`
2. Use YAML frontmatter:
   ```yaml
   ---
   title: "Paper Title"
   collection: publications
   permalink: /publications/SHORT-NAME
   date: YYYY-MM-DD
   venue: 'Venue Name'
   paperurl: 'https://link-to-paper'
   ---
   ```
3. Add abstract and content below frontmatter

Alternatively, for batch additions:
1. Add entry to `markdown_generator/publications.tsv`
2. Run `python markdown_generator/publications.py` or execute the Jupyter notebook

### Adding Static Pages
Create markdown files in `_pages/` with appropriate frontmatter. Use `permalink` to define URL structure.

### Updating Author Info
Edit the `author:` section in `_config.yml` to update bio, social links, and contact information.

## Theme Customization
This site uses the Minimal Mistakes theme via github-pages gem. The theme is configured through `_config.yml`. Layout defaults are defined per collection type in the `defaults:` section.

## Deployment
The site is deployed via GitHub Pages. Push to the main branch to trigger deployment. Jekyll builds automatically on GitHub's servers using the github-pages gem configuration.
=======
# Install dependencies
bundle install

# Serve the site locally with development config (disables analytics)
bundle exec jekyll serve --config _config.yml,_config.dev.yml

# Serve with production config
bundle exec jekyll serve

# Build the site
bundle exec jekyll build
```

### JavaScript Build (if needed)
```bash
# Install npm dependencies
npm install

# Build/minify JavaScript
npm run build:js

# Watch for JavaScript changes
npm run watch:js
```

## Site Architecture

### Jekyll Collections
The site uses five Jekyll collections defined in `_config.yml`:
- **`_publications/`** - Research publications with abstracts, excerpts, and metadata
- **`_posts/`** - Blog posts following `YYYY-MM-DD-title.md` naming convention
- **`_talks/`** - Conference talks and presentations
- **`_teaching/`** - Teaching materials and courses
- **`_portfolio/`** - Portfolio projects

### Key Directories
- **`_pages/`** - Static pages (about, awards, contact, etc.). Note: `about.md` is the homepage (permalink: `/`)
- **`_layouts/`** - Page templates (`single.html`, `talk.html`, `archive.html`, etc.)
- **`_includes/`** - Reusable components (author profile, analytics, navigation, etc.)
- **`_sass/`** - Sass stylesheets
- **`_data/`** - YAML data files for structured content
- **`images/`** - Image assets
- **`files/`** - Downloadable files (PDFs, etc.)
- **`_site/`** - Generated site output (excluded from git)

### Configuration Files
- **`_config.yml`** - Main production configuration (site metadata, author info, collections, plugins)
- **`_config.dev.yml`** - Development overrides (disables analytics, uses localhost URL)
- **`Gemfile`** - Ruby dependencies (uses `github-pages` gem for compatibility)
- **`package.json`** - npm build scripts for JavaScript minification

## Content Structure

### Publications Format
Publications in `_publications/` use frontmatter:
```yaml
---
title: "Publication Title"
excerpt: "<p align='center'><a href='/publications/SLUG'><img src='/images/SLUG.png' style='width: 500px;'/></a></p>"
collection: publications
permalink: /publications/SLUG
date: YYYY-MM-DD
venue: 'Conference/Journal Name'
---
```

### Blog Posts Format
Posts in `_posts/` follow Jekyll conventions:
```yaml
---
title: 'Post Title'
date: YYYY-MM-DD
permalink: /posts/YYYY/MM/blog-post-slug/
tags:
  - tag1
  - tag2
---
```

### Homepage
The homepage is `_pages/about.md` with `permalink: /`. When updating the homepage, edit this file, not `index.html`.

## Important Configuration Details

### Site Settings
- **Base URL**: https://yiyangwan.github.io
- **Timezone**: America/Los_Angeles
- **Markdown**: kramdown with GFM input
- **Highlighter**: rouge

### Plugins
Active Jekyll plugins:
- jekyll-paginate
- jekyll-gist
- jekyll-feed
- jekyll-redirect-from
- jekyll-sitemap (from GitHub)

### Author Profile
Author information is centralized in `_config.yml` under the `author:` section. This populates the sidebar on all pages.

## Deployment

The site is deployed via GitHub Pages. Pushing to the `main` branch automatically triggers a rebuild. The generated site serves from the repository root, not a `/docs` folder.

## Notes

- When adding new publications, ensure images are placed in `/images/` and referenced correctly in the excerpt
- The site uses the `future: false` setting, so posts dated in the future won't be published
- Development mode (`_config.dev.yml`) disables Google Analytics for local testing
- The JavaScript build process concatenates and minifies multiple vendor libraries and custom scripts into `assets/js/main.min.js`
>>>>>>> Stashed changes
