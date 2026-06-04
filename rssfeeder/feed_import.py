"""Import items from an external RSS or Atom feed URL."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any, Optional
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from rssfeeder.config import FeedConfig
from rssfeeder.scrape import FeedItem, _item_description

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_STRIP_TAGS = re.compile(r"<[^>]+>")


def _parse_datetime(raw: str) -> datetime:
    parsed = date_parser.parse(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _plain_text(value: str) -> str:
    text = html.unescape(_STRIP_TAGS.sub("", value))
    return re.sub(r"\s+", " ", text).strip()


def _normalize_url(raw: str, base_url: str) -> Optional[str]:
    src = html.unescape(raw.strip())
    if not src or src.startswith("data:"):
        return None
    if src.startswith("//"):
        return f"https:{src}"
    if src.startswith("/"):
        from urllib.parse import urljoin

        return urljoin(base_url, src)
    return src


def _first_image_from_html(fragment: str, base_url: str) -> Optional[str]:
    if not fragment or "<img" not in fragment:
        return None
    soup = BeautifulSoup(fragment, "lxml")
    for img in soup.select("img[src], img[data-src]"):
        for attr in ("src", "data-src"):
            url = _normalize_url(img.get(attr, ""), base_url)
            if url:
                return url
    return None


def _atom_content_html(entry: ET.Element) -> str:
    """Prefer full HTML content over short summary (The Verge puts images only in content)."""
    content_html = ""
    summary_html = ""
    for child in entry:
        name = _local_name(child.tag)
        if name == "content":
            content_html = (child.text or "").strip()
        elif name == "summary":
            summary_html = (child.text or "").strip()
    if content_html and "<img" in content_html:
        return content_html
    if content_html:
        return content_html
    return summary_html


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _atom_text(parent: ET.Element, name: str) -> str:
    for child in parent:
        if _local_name(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _atom_entries(root: ET.Element) -> list[ET.Element]:
    if _local_name(root.tag) == "feed":
        return [el for el in root if _local_name(el.tag) == "entry"]
    channel = root.find("channel")
    if channel is not None:
        return [el for el in channel if _local_name(el.tag) == "item"]
    return []


def _parse_atom_entry(entry: ET.Element, config: FeedConfig) -> Optional[FeedItem]:
    title = _plain_text(_atom_text(entry, "title"))
    link = ""
    for child in entry:
        if _local_name(child.tag) == "link" and child.get("rel") in (None, "alternate"):
            link = child.get("href", "").strip()
            if link:
                break
    if not title or not link:
        return None

    published_raw = _atom_text(entry, "published") or _atom_text(entry, "updated")
    if not published_raw:
        return None
    published = _parse_datetime(published_raw)

    author = ""
    for child in entry:
        if _local_name(child.tag) == "author":
            author = _atom_text(child, "name")
            break

    categories = [
        child.get("term", "").strip()
        for child in entry
        if _local_name(child.tag) == "category" and child.get("term")
    ]
    category = categories[0] if categories else None

    content_html = _atom_content_html(entry)

    guid = _atom_text(entry, "id") or link
    image_url = _first_image_from_html(content_html, config.page_url)
    if content_html:
        description_html = content_html
        if image_url and "<img" not in content_html.lower():
            description_html = _item_description(title, author or None, image_url, category) + content_html
    else:
        description_html = _item_description(title, author or None, image_url, category)

    return FeedItem(
        guid=guid,
        title=title,
        link=link,
        published=published,
        author=author or None,
        description_html=description_html,
        image_url=image_url,
        comments_url=None,
        category=category,
    )


def _parse_rss_item(item: ET.Element, config: FeedConfig) -> Optional[FeedItem]:
    def child_text(name: str) -> str:
        el = item.find(name)
        return (el.text or "").strip() if el is not None else ""

    title = _plain_text(child_text("title"))
    link = child_text("link")
    if not title or not link:
        return None

    published_raw = child_text("pubDate") or child_text("date")
    if not published_raw:
        return None

    author = child_text("author") or None
    category = child_text("category") or None
    guid = child_text("guid") or link
    content_html = child_text("description")
    image_url = _first_image_from_html(content_html, config.page_url)
    description_html = content_html or _item_description(title, author, image_url, category)

    return FeedItem(
        guid=guid,
        title=title,
        link=link,
        published=_parse_datetime(published_raw),
        author=author,
        description_html=description_html,
        image_url=image_url,
        comments_url=None,
        category=category,
    )


def import_feed_items(config: FeedConfig) -> list[FeedItem]:
    if not config.source_feed_url:
        raise ValueError("source_feed_url is required")

    response = requests.get(
        config.source_feed_url,
        headers={"User-Agent": config.user_agent},
        timeout=30,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items: list[FeedItem] = []

    if _local_name(root.tag) == "feed":
        for entry in _atom_entries(root):
            item = _parse_atom_entry(entry, config)
            if item is not None:
                items.append(item)
    else:
        for entry in _atom_entries(root):
            item = _parse_rss_item(entry, config)
            if item is not None:
                items.append(item)

    if config.item_sort == "date":
        items.sort(key=lambda item: item.published, reverse=True)
    return items
