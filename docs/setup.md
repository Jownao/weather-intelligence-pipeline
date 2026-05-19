# Building and Serving Docs Locally

This document explains how to build and serve the MkDocs documentation site on your local machine.

## Prerequisites

- Python 3.11+
- `pip`

## Setup

1. Install MkDocs and the Material theme:

```bash
pip install -r requirements-dev.txt
```

Or, if you prefer only MkDocs:

```bash
pip install mkdocs mkdocs-material
```

2. Build the static site:

```bash
mkdocs build
```

This creates a `site/` folder with the rendered HTML.

## Serve Locally

To view the docs in real-time as you edit:

```bash
mkdocs serve
```

Then open `http://localhost:8000` in your browser.

## Deploy

Once you are happy with the docs:

1. Build the final site:

```bash
mkdocs build
```

2. The `site/` folder can be:
   - Uploaded to your web host
   - Deployed to GitHub Pages (manually via actions or other CI/CD)
   - Served from a static file server
   - Committed to a separate branch (`gh-pages`) for GitHub Pages

Example: to set up GitHub Pages to serve from `gh-pages` branch:

```bash
git add site/
git commit -m "docs: build mkdocs site"
git subtree push --prefix site origin gh-pages
```

Then in GitHub Settings → Pages, set the branch to `gh-pages` and folder to `/ (root)`.
