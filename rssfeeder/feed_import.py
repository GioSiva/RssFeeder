"""Import items from an external RSS or Atom feed URL."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from rssfeeder.config import FeedConfig
from rssfeeder.scrape import FeedItem, _item_description, _prefer_rss_image_url

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_STRIP_TAGS = re.compile(r"<[^>]+>")
_BLOGGER_SIZE = re.compile(r"/s\d+(?:-[^/]+)?/", re.I)
_AD_IMAGE_HOSTS = ("linksynergy.com", "doubleclick.net", "googleads.")


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


def _is_ad_image_url(url: str) -> bool:
    lower = url.lower()
    return any(host in lower for host in _AD_IMAGE_HOSTS)


def _rss_safe_image_url(url: str) -> str:
    """Encode path and normalize Blogger CDN URLs for picky RSS readers (Opera, e-ink)."""
    parts = urlsplit(url)
    path = quote(unquote(parts.path), safe="/")
    normalized = urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    if "googleusercontent.com" not in normalized:
        return normalized
    normalized = _BLOGGER_SIZE.sub("/s1600/", normalized)
    if normalized.lower().endswith(".webp"):
        normalized = normalized[:-5] + ".jpg"
    return normalized


def _collect_image_candidates_from_html(fragment: str, base_url: str) -> list[str]:
    if not fragment or "<img" not in fragment:
        return []
    soup = BeautifulSoup(fragment, "lxml")
    candidates: list[str] = []
    seen: set[str] = set()

    def add(raw: Optional[str]) -> None:
        url = _normalize_url(raw or "", base_url)
        if not url or url in seen or _is_ad_image_url(url):
            return
        seen.add(url)
        candidates.append(url)

    for img in soup.select("img[src], img[data-src]"):
        for attr in ("src", "data-src"):
            add(img.get(attr))
        parent = img.find_parent("a")
        if parent is not None:
            add(parent.get("href"))

    return candidates


def _best_image_from_html(fragment: str, base_url: str) -> Optional[str]:
    candidates = _collect_image_candidates_from_html(fragment, base_url)
    if not candidates:
        return None
    chosen = _prefer_rss_image_url(candidates, base_url)
    return _rss_safe_image_url(chosen) if chosen else None


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


def _pick_atom_category(categories: list[str]) -> Optional[str]:
    if not categories:
        return None
    for term in categories:
        if term.strip().upper() == "NOVIDADES MANGA":
            return term
    return categories[0]


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
    if author and author.strip().lower() == "unknown":
        author = ""

    categories = [
        child.get("term", "").strip()
        for child in entry
        if _local_name(child.tag) == "category" and child.get("term")
    ]
    category = _pick_atom_category(categories)

    content_html = _atom_content_html(entry)

    guid = _atom_text(entry, "id") or link
    image_url = _best_image_from_html(content_html, config.page_url)
    # Simple <img> + text — Opera GX and most readers ignore <figure> blocks from Atom.
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
    image_url = _best_image_from_html(content_html, config.page_url)
    description_html = _item_description(title, author, image_url, category)

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
