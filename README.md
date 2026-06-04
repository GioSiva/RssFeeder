# RssFeeder

RSS feeds for custom webpages — scrape article lists from HTML and expose them as RSS 2.0.

## PokeBeach preset

Reads articles from the [PokeBeach](https://www.pokebeach.com/) homepage inside `.xpress_articleList` (each `<article>` block).

Extracted fields per item:

- Title and link (`h2.entry-title a`)
- Author (`a.article__author`)
- Published date (`.entry-meta a[rel="bookmark"]`)
- Featured image (`.xpress_articleImage--full img`)
- Comments link (optional)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### HTTP server (recommended)

```bash
python -m rssfeeder
```

Open:

- Index: http://127.0.0.1:8080/
- Feed: http://127.0.0.1:8080/feed/pokebeach.xml

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RSSFEEDER_HOST` | `127.0.0.1` | Bind address |
| `RSSFEEDER_PORT` | `8080` | Bind port |
| `RSSFEEDER_SITE_URL` | `http://127.0.0.1:8080` | Canonical site URL in feed metadata |
| `RSSFEEDER_CACHE_TTL` | `900` | Seconds to cache fetched HTML |

### One-shot CLI

```bash
python -m rssfeeder.cli pokebeach > pokebeach.xml
```

## Tests

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

## Custom feeds

Add a YAML file under `rssfeeder/presets/<name>.yaml` with selectors matching your target page. See `rssfeeder/presets/pokebeach.yaml` for the pattern.
