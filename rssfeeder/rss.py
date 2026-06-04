from __future__ import annotations

from feedgen.feed import FeedGenerator

from rssfeeder.config import FeedConfig
from rssfeeder.scrape import FeedItem


def _mime_for_image(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    return "image/*"


def build_rss(config: FeedConfig, items: list[FeedItem]) -> str:
    fg = FeedGenerator()
    fg.id(config.feed_url)
    fg.title(config.title)
    fg.link(href=config.page_url, rel="alternate")
    fg.description(config.description)
    fg.language(config.language)

    # feedgen emits entries in reverse insertion order; page scrape is newest-first
    for item in reversed(items):
        entry = fg.add_entry()
        entry.id(item.guid)
        entry.title(item.title)
        entry.link(href=item.link)
        entry.published(item.published)
        entry.updated(item.published)
        entry.description(item.description_html, isSummary=False)

        if item.author:
            entry.author(name=item.author)

        if item.category:
            entry.category(term=item.category)

        if item.image_url:
            entry.enclosure(item.image_url, 0, _mime_for_image(item.image_url))

        if item.comments_url:
            entry.comments(item.comments_url)

    return fg.rss_str(pretty=True).decode("utf-8")
