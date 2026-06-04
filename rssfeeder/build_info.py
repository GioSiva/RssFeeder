"""Write build-info.json summarizing generated feeds for the GitHub Pages index."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _summarize_feed(path: Path) -> dict:
    root = ET.parse(path).getroot()
    channel = root.find("channel")
    if channel is None:
        raise ValueError(f"No RSS channel in {path}")

    title = ""
    last_build = ""
    categories: dict[str, int] = {}
    sample_titles: list[dict[str, str]] = []
    item_count = 0

    for child in channel:
        name = _local_name(child.tag)
        if name == "title" and not title:
            title = (child.text or "").strip()
        elif name == "lastBuildDate":
            last_build = (child.text or "").strip()
        elif name == "item":
            item_count += 1
            item_title = ""
            item_category = ""
            for part in child:
                part_name = _local_name(part.tag)
                if part_name == "title":
                    item_title = (part.text or "").strip()
                elif part_name == "category":
                    item_category = (part.text or "").strip()
            if item_category:
                categories[item_category] = categories.get(item_category, 0) + 1
            if item_title and len(sample_titles) < 8:
                sample_titles.append(
                    {"title": item_title, "category": item_category or "(sem categoria)"}
                )

    return {
        "file": path.name,
        "title": title,
        "lastBuildDate": last_build,
        "itemCount": item_count,
        "categories": categories,
        "sampleItems": sample_titles,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize RSS XML files for build-info.json")
    parser.add_argument("output", type=Path, help="JSON output path")
    parser.add_argument("feeds", nargs="+", type=Path, help="RSS XML files to summarize")
    args = parser.parse_args(argv)

    feeds = [_summarize_feed(path) for path in args.feeds]
    payload = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "feeds": feeds,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
