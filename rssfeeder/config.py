from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PRESETS_DIR = Path(__file__).resolve().parent / "presets"


@dataclass(frozen=True)
class FeedConfig:
    """CSS selectors and metadata for building an RSS feed from a page."""

    id: str
    title: str
    site_url: str
    page_url: str
    description: str
    list_selector: str = ".xpress_articleList article"
    item_title_selector: str = "h2.entry-title a"
    item_link_selector: str = "h2.entry-title a"
    item_author_selector: str = "a.article__author"
    item_date_selector: str = '.entry-meta a[rel="bookmark"]'
    item_image_selector: str = ".xpress_articleImage--full img"
    item_comments_selector: str = '.entry-meta a[href*="#comments"]'
    item_date_attribute: str = ""
    max_pages: int = 1
    # query: ?page=N (default). path: WordPress-style /page/N/ under page_url.
    pagination: str = "query"
    item_sort: str = "date"
    # Path under site_url where this feed is served (e.g. feed/gameinformer.xml).
    feed_public_path: str = ""
    # WordPress REST API (optional): when wp_category_id > 0, fetch posts via JSON.
    wp_category_id: int = 0
    wp_per_page: int = 100
    exclude_category_ids: str = ""
    exclude_link_substrings: str = ""
    stop_at_link_contains: str = ""
    section_start_heading: str = ""
    section_stop_heading: str = ""
    # Stop after the first widget whose text includes this label (e.g. «Mostrar mais»).
    section_stop_at_text: str = ""
    # Comma-separated heading labels; matching widgets are skipped (scan continues).
    section_skip_headings: str = ""
    # Comma-separated headings that end the scan immediately.
    section_hard_stop_headings: str = ""
    user_agent: str = "RssFeeder/1.0 (+https://github.com/GioSiva/RssFeeder)"
    language: str = "en"

    @property
    def feed_url(self) -> str:
        path = self.feed_public_path or f"feed/{self.id}.xml"
        return f"{self.site_url.rstrip('/')}/{path.lstrip('/')}"


def load_preset(preset_id: str) -> FeedConfig:
    path = PRESETS_DIR / f"{preset_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown feed preset: {preset_id}")
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return FeedConfig(**data)
