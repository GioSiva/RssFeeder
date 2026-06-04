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
    user_agent: str = "RssFeeder/1.0 (+https://github.com/GioSiva/RssFeeder)"
    language: str = "en"

    @property
    def feed_url(self) -> str:
        return f"{self.site_url.rstrip('/')}/feed/{self.id}.xml"


def load_preset(preset_id: str) -> FeedConfig:
    path = PRESETS_DIR / f"{preset_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Unknown feed preset: {preset_id}")
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return FeedConfig(**data)
