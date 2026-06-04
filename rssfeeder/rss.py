from __future__ import annotations

from feedgen.feed import FeedGenerator

from rssfeeder.config import FeedConfig
from rssfeeder.scrape import FeedItem, format_rfc822


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

        if item.image_url:
            entry.enclosure(item.image_url, 0, "image/png")

        if item.comments_url:
            entry.comments(item.comments_url)

    return fg.rss_str(pretty=True).decode("utf-8")
