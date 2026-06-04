# AGENTS.md

Guidance for AI agents working in this repository.

## Project

**RssFeeder** — generates custom RSS 2.0 feeds by scraping article lists from HTML (e.g. PokeBeach `.xpress_articleList`).

Stack: Python 3.12, Flask, BeautifulSoup, feedgen.

## Cursor Cloud specific instructions

### Services

| Service | Command | Port |
|---------|---------|------|
| RSS HTTP server | `python -m rssfeeder` | 8080 (default) |

### Dependencies

```bash
pip install -r requirements.txt
```

The VM update script runs `pip install -r requirements.txt` when that file exists.

### Lint / test

```bash
python -m unittest discover -s tests -v
```

No separate linter is configured yet.

### GitHub Pages

Production feed URLs (after merge to `main` + Pages enabled):

- Canonical: `https://giosiva.github.io/RssFeeder/feed/pokebeach.xml` (and `feed/gameinformer.xml`)
- Legacy copy at repo root: `pokebeach.xml`, `gameinformer.xml` (same content)
- Index with deploy verification: `https://giosiva.github.io/RssFeeder/`

Many RSS readers re-sort by `pubDate`; Game Informer XML keeps website DOM order but newer News may still appear first in the app.

Workflow: `.github/workflows/publish-feed.yml` (hourly cron + push to `main`).

### Run / demo (local)

```bash
python -m rssfeeder
curl -s http://127.0.0.1:8080/feed/pokebeach.xml | head -40
```

One-shot feed without server:

```bash
python -m rssfeeder.cli pokebeach | head -40
```

Set `RSSFEEDER_SITE_URL` when deploying behind a public hostname so feed `<link>` metadata is correct.

### Adding feeds

Create `rssfeeder/presets/<id>.yaml` with CSS selectors; expose at `/feed/<id>.xml`.
