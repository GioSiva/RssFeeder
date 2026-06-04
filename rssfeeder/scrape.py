from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

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


def _href(el: Optional[Tag], base_url: str) -> Optional[str]:
    if el is None:
        return None
    raw = el.get("href")
    if not raw:
        return None
    return urljoin(base_url, raw)


def _img_src(el: Optional[Tag], base_url: str) -> Optional[str]:
    if el is None:
        return None
    raw = el.get("src") or el.get("data-src")
    if not raw:
        return None
    return urljoin(base_url, raw)


def _published(date_el: Optional[Tag], config: FeedConfig) -> Optional[datetime]:
    if date_el is None:
        return None
    if config.item_date_attribute:
        raw = date_el.get(config.item_date_attribute)
        if raw:
            return _parse_published(raw)
    date_text = _text(date_el)
    if not date_text:
        return None
    return _parse_published(date_text)


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
        date_el = article.select_one(config.item_date_selector)
        image_el = article.select_one(config.item_image_selector)

        title = _text(title_el)
        link = _href(link_el, config.page_url)
        if not title or not link:
            continue

        published = _published(date_el, config)
        if published is None:
            continue

        author_el = (
            article.select_one(config.item_author_selector)
            if config.item_author_selector
            else None
        )
        comments_el = (
            article.select_one(config.item_comments_selector)
            if config.item_comments_selector
            else None
        )

        guid = (
            article.get("id")
            or (f"gi-{article.get('data-id')}" if article.get("data-id") else None)
            or link
        )
        author = _text(author_el)
        image_url = _img_src(image_el, config.page_url)
        comments_url = _href(comments_el, config.page_url)

        items.append(
            FeedItem(
                guid=guid,
                title=title,
                link=link,
                published=published,
                author=author,
                description_html=_item_description(title, author, image_url),
                image_url=image_url,
                comments_url=comments_url,
            )
        )

    return items
