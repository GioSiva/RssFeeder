from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from rssfeeder.config import FeedConfig

DATE_CLEANUP = re.compile(r"^\s*Posted on\s*", re.I)


@dataclass(frozen=True)
class FeedItem:
    guid: str
    title: str
    link: str
    published: datetime
    author: Optional[str]
    description_html: str
    image_url: Optional[str]
    comments_url: Optional[str]


def _parse_published(text: str) -> datetime:
    cleaned = DATE_CLEANUP.sub("", text.strip())
    parsed = date_parser.parse(cleaned)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _text(el: Optional[Tag]) -> Optional[str]:
    if el is None:
        return None
    value = el.get_text(strip=True)
    return value or None


def _href(el: Optional[Tag]) -> Optional[str]:
    if el is None:
        return None
    return el.get("href") or None


def _img_src(el: Optional[Tag]) -> Optional[str]:
    if el is None:
        return None
    return el.get("src") or el.get("data-src")


def _item_description(title: str, author: Optional[str], image_url: Optional[str]) -> str:
    parts: list[str] = []
    if image_url:
        parts.append(f'<p><img src="{image_url}" alt="" /></p>')
    if author:
        parts.append(f"<p>By {author}</p>")
    parts.append(f"<p>{title}</p>")
    return "\n".join(parts)


def scrape_items(config: FeedConfig, *, html: Optional[str] = None) -> list[FeedItem]:
    if html is None:
        response = requests.get(
            config.page_url,
            headers={"User-Agent": config.user_agent},
            timeout=30,
        )
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "lxml")
    articles = soup.select(config.list_selector)

    items: list[FeedItem] = []
    for article in articles:
        if not isinstance(article, Tag):
            continue

        title_el = article.select_one(config.item_title_selector)
        link_el = article.select_one(config.item_link_selector)
        author_el = article.select_one(config.item_author_selector)
        date_el = article.select_one(config.item_date_selector)
        image_el = article.select_one(config.item_image_selector)
        comments_el = article.select_one(config.item_comments_selector)

        title = _text(title_el)
        link = _href(link_el)
        if not title or not link:
            continue

        date_text = _text(date_el)
        if not date_text:
            continue

        guid = article.get("id") or link
        author = _text(author_el)
        image_url = _img_src(image_el)
        comments_url = _href(comments_el)

        items.append(
            FeedItem(
                guid=guid,
                title=title,
                link=link,
                published=_parse_published(date_text),
                author=author,
                description_html=_item_description(title, author, image_url),
                image_url=image_url,
                comments_url=comments_url,
            )
        )

    return items
