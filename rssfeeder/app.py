from __future__ import annotations

import os
import time
from dataclasses import replace

from flask import Flask, Response, jsonify

from rssfeeder.config import FeedConfig, load_preset
from rssfeeder.rss import build_rss
from rssfeeder.scrape import scrape_items

CACHE_TTL_SECONDS = int(os.environ.get("RSSFEEDER_CACHE_TTL", "900"))

_cache: dict[str, tuple[float, str]] = {}


def _site_base_url() -> str:
    return os.environ.get("RSSFEEDER_SITE_URL", "http://127.0.0.1:8080").rstrip("/")


def _with_runtime_site_url(config: FeedConfig) -> FeedConfig:
    return replace(config, site_url=_site_base_url())


def _cached_feed(config: FeedConfig) -> str:
    key = config.id
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    items = scrape_items(config)
    xml = build_rss(config, items)
    _cache[key] = (now, xml)
    return xml


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return jsonify(
            {
                "name": "RssFeeder",
                "feeds": {
                    "pokebeach": f"{_site_base_url()}/feed/pokebeach.xml",
                },
            }
        )

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/feed/<preset_id>.xml")
    def feed(preset_id: str):
        try:
            config = _with_runtime_site_url(load_preset(preset_id))
        except FileNotFoundError:
            return jsonify({"error": f"Unknown feed: {preset_id}"}), 404

        try:
            xml = _cached_feed(config)
        except Exception as exc:  # noqa: BLE001 — surface fetch/parse errors to client
            return jsonify({"error": str(exc)}), 502

        return Response(xml, mimetype="application/rss+xml; charset=utf-8")

    return app


def main() -> None:
    host = os.environ.get("RSSFEEDER_HOST", "127.0.0.1")
    port = int(os.environ.get("RSSFEEDER_PORT", "8080"))
    create_app().run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
