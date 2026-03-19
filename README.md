# HassOS Apps — Website

> Source for [hassos-apps.github.io](https://hassos-apps.github.io) — the public showcase for the HassOS Apps ecosystem.

[![Deploy to GitHub Pages](https://github.com/hassos-apps/website/actions/workflows/deploy.yml/badge.svg)](https://github.com/hassos-apps/website/actions/workflows/deploy.yml)
[![Sync Apps](https://github.com/hassos-apps/website/actions/workflows/sync-apps.yml/badge.svg)](https://github.com/hassos-apps/website/actions/workflows/sync-apps.yml)

## Overview

Static website built with **Jekyll** + **Tailwind CSS**, hosted on GitHub Pages.
App data is automatically kept in sync with the [hassos-apps/repository](https://github.com/hassos-apps/repository) via a scheduled GitHub Actions workflow.

## Tech stack

| Layer | Technology |
|-------|-----------|
| Static site generator | Jekyll ~4.3 |
| CSS framework | Tailwind CSS 3.x |
| Hosting | GitHub Pages |
| Data sync | Python 3 script + GitHub Actions |

## Local development

### Prerequisites

- Node.js ≥ 18
- Ruby ≥ 3.2 + Bundler

### Setup

```bash
# Install Node dependencies (Tailwind)
npm install

# Install Ruby dependencies (Jekyll)
bundle install
```

### Run

```bash
# Terminal 1 — watch Tailwind CSS
npm run dev

# Terminal 2 — serve Jekyll site
bundle exec jekyll serve --livereload
```

Open [http://localhost:4000](http://localhost:4000).

### Build (production)

```bash
npm run build:css
bundle exec jekyll build
```

Output is written to `_site/`.

### Quality checks

```bash
python scripts/check-site.py
```

This validates a few non-negotiable conventions:
- homepage composed via Jekyll includes/layouts
- SEO/layout hooks are present
- no hardcoded root links or inline page scripts
- shared frontend script and accessibility helpers remain wired

## Data pipeline

App metadata is stored in `_data/apps.yml` and rendered by Jekyll templates.
It is **auto-generated** — do not edit manually.

To refresh locally:

```bash
python3 scripts/sync-apps.py
```

In CI, the `Sync Apps from Repository` workflow runs every 6 hours and can also be triggered manually or via a `repository_dispatch` webhook from [hassos-apps/repository](https://github.com/hassos-apps/repository).

## Project structure

```
.
├── _includes/          # Reusable homepage sections and shared partials
├── _layouts/           # Shared Jekyll layouts
├── _data/
│   └── apps.yml          # Auto-generated app list (do not edit)
├── assets/
│   ├── css/
│   │   ├── input.css     # Tailwind source
│   │   └── style.css     # Compiled output (gitignored in dev)
│   └── js/
│       └── site.js       # Shared frontend interactions
├── scripts/
│   ├── check-site.py     # Lightweight project quality checks
│   └── sync-apps.py      # Fetches app metadata from hassos-apps/repository
├── .github/
│   └── workflows/
│       ├── deploy.yml    # Build + deploy to GitHub Pages
│       └── sync-apps.yml # Sync _data/apps.yml on schedule
├── index.html            # Homepage assembly entrypoint
├── 404.html              # Custom 404 page
├── _config.yml           # Jekyll configuration
├── Gemfile               # Ruby dependencies
├── package.json          # Node dependencies
└── tailwind.config.js    # Tailwind configuration
```

## Contributing

This repository contains only the website source.
To contribute an app to the ecosystem, see [hassos-apps/repository](https://github.com/hassos-apps/repository) and the [Developer Guide](https://github.com/hassos-apps/docs).

## License

[MIT](LICENSE) © HassOS Apps
