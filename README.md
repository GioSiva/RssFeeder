# RssFeeder

RSS feeds for custom webpages — scrape article lists from HTML and expose them as RSS 2.0.

## Presets

### PokeBeach

Reads articles from the [PokeBeach](https://www.pokebeach.com/) homepage inside `.xpress_articleList` (each `<article>` block).

Extracted fields per item:

- Title and link (`h2.entry-title a`)
- Author (`a.article__author`)
- Published date (`.entry-meta a[rel="bookmark"]`)
- Featured image (`.xpress_articleImage--full img`)
- Comments link (optional)

### Game Informer

Reads news teasers from [Game Informer News](https://gameinformer.com/news) (`article.node--view-mode-teaser`).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## GitHub Pages (sem instalar nada)

Depois de fazer merge para `main` e ativar **GitHub Pages** (Settings → Pages → Source: **GitHub Actions**), o workflow publica o feed automaticamente:

| Recurso | URL |
|---------|-----|
| PokeBeach | https://giosiva.github.io/RssFeeder/pokebeach.xml |
| Game Informer | https://giosiva.github.io/RssFeeder/gameinformer.xml |
| Página inicial | https://giosiva.github.io/RssFeeder/ |

O workflow `.github/workflows/publish-feed.yml` corre **de hora a hora** (e em cada push para `main`). Pode também disparar manualmente em Actions → *Publish RSS to GitHub Pages* → *Run workflow*.

No leitor RSS (Feedly, NetNewsWire, etc.), use o URL do feed acima.

## Usage

### HTTP server (local)

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
