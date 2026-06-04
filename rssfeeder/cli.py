"""Generate an RSS feed to stdout without running the HTTP server."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace

from rssfeeder.config import load_preset
from rssfeeder.rss import build_rss
from rssfeeder.scrape import scrape_items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a custom RSS feed from a webpage.")
    parser.add_argument(
        "preset",
        nargs="?",
        default="pokebeach",
        help="Feed preset name (default: pokebeach)",
    )
    parser.add_argument(
        "--site-url",
        default=os.environ.get("RSSFEEDER_SITE_URL", "http://127.0.0.1:8080"),
        help="Base URL embedded in feed metadata",
    )
    parser.add_argument(
        "--feed-public-path",
        default=os.environ.get("RSSFEEDER_FEED_PUBLIC_PATH", ""),
        help="Public path for this feed under site-url (default: feed/<preset>.xml)",
    )
    args = parser.parse_args(argv)

    try:
        config = replace(
            load_preset(args.preset),
            site_url=args.site_url.rstrip("/"),
            feed_public_path=args.feed_public_path,
        )
    except FileNotFoundError:
        print(f"Unknown preset: {args.preset}", file=sys.stderr)
        return 1

    items = scrape_items(config)
    sys.stdout.write(build_rss(config, items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
