# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Jekyll-based personal academic website for Yiyang Wang, hosted on GitHub Pages. The site uses the Minimal Mistakes theme and is structured around Jekyll collections for organizing academic content (publications, talks, teaching, portfolio).

## Development Commands

### Local Development
```bash
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
