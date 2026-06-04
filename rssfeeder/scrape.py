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
TITLE_FALLBACK_SELECTORS = (
    ".field--name-field-promo-headline",
    'span[property="schema:name"]',
    "h2.page-title a",
    "h3.page-title a",
    "a[rel=bookmark]",
)
SECTION_SELECTORS = (
    ".bug-wrapper.article-section",
    ".gi5-field-bug.field__item",
    ".field--name-field-bug .field__item",
    ".meta-categories a",
)


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
    category: Optional[str] = None


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


def _split_selectors(selector_list: str) -> list[str]:
    return [part.strip() for part in selector_list.split(",") if part.strip()]


def _select_first(parent: Tag, selector_list: str) -> Optional[Tag]:
    for selector in _split_selectors(selector_list):
        el = parent.select_one(selector)
        if el is not None:
            return el
    return None


def _href(el: Optional[Tag], base_url: str) -> Optional[str]:
    if el is None:
        return None
    raw = el.get("href")
    if not raw:
        return None
    return urljoin(base_url, raw)


def _first_url_from_srcset(srcset: str) -> Optional[str]:
    urls: list[str] = []
    for part in srcset.split(","):
        piece = part.strip().split()
        if piece:
            urls.append(piece[0])
    if not urls:
        return None
    return urls[-1]


def _resolve_image(article: Tag, base_url: str, image_selector: str) -> Optional[str]:
    root = (
        _select_first(article, image_selector)
        if image_selector
        else article.select_one(".field--name-field-promo-image")
    )
    if root is None:
        root = article.select_one(".field--name-field-promo-image")
    if root is None:
        return None

    picture = root if root.name == "picture" else root.select_one("picture")
    if picture:
        preferred: list[Tag] = []
        fallback: list[Tag] = []
        for source in picture.select("source"):
            srcset = source.get("srcset")
            if not srcset:
                continue
            media = source.get("media", "")
            if "min-width: 851px" in media or "min-width: 1200px" in media:
                preferred.append(source)
            else:
                fallback.append(source)
        for source in preferred + fallback:
            srcset = source.get("srcset")
            if srcset:
                url = _first_url_from_srcset(srcset)
                if url:
                    return urljoin(base_url, url)
        img = picture.select_one("img")
        if img and img.get("src"):
            return urljoin(base_url, img["src"])

    if root.name == "img" and root.get("src"):
        return urljoin(base_url, root["src"])
    img = root.select_one("img")
    if img and img.get("src"):
        return urljoin(base_url, img["src"])
    return None


def _resolve_title(article: Tag, primary_selector: str) -> Optional[str]:
    for selector in _split_selectors(primary_selector) + list(TITLE_FALLBACK_SELECTORS):
        el = article.select_one(selector)
        if el is not None:
            title = _text(el)
            if title:
                return title
    return None


def _resolve_link(article: Tag, link_selector: str, base_url: str) -> Optional[str]:
    el = _select_first(article, link_selector)
    link = _href(el, base_url)
    if link:
        return link
    about = article.get("about")
    if about:
        return urljoin(base_url, about)
    return None


def _resolve_section(article: Tag) -> Optional[str]:
    for selector in SECTION_SELECTORS:
        el = article.select_one(selector)
        section = _text(el)
        if section:
            return section
    return None


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


def _item_description(
    title: str,
    author: Optional[str],
    image_url: Optional[str],
    category: Optional[str],
) -> str:
    parts: list[str] = []
    if image_url:
        parts.append(f'<p><img src="{image_url}" alt="" /></p>')
    if category:
        parts.append(f"<p><em>{category}</em></p>")
    if author:
        parts.append(f"<p>By {author}</p>")
    parts.append(f"<p>{title}</p>")
    return "\n".join(parts)


def _wordpress_post_guid(article: Tag) -> Optional[str]:
    for cls in article.get("class") or []:
        if cls.startswith("post-") and cls[5:].isdigit():
            return cls
    return None


def _article_key(article: Tag, link: str) -> str:
    if article.get("data-id"):
        return f"gi-{article.get('data-id')}"
    wp_guid = _wordpress_post_guid(article)
    if wp_guid:
        return wp_guid
    return link


def _fetch_html(url: str, config: FeedConfig) -> str:
    response = requests.get(
        url,
        headers={"User-Agent": config.user_agent},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _listing_urls(config: FeedConfig) -> list[str]:
    if config.max_pages <= 1:
        return [config.page_url]
    base = config.page_url.split("?", 1)[0].rstrip("/")
    if config.pagination == "path":
        return [config.page_url] + [f"{base}/page/{page}/" for page in range(2, config.max_pages + 1)]
    return [config.page_url] + [f"{base}?page={page}" for page in range(2, config.max_pages + 1)]


def _scrape_page_html(
    config: FeedConfig,
    html: str,
    items: list[FeedItem],
    seen: set[str],
) -> None:
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select(config.list_selector)

    for article in articles:
        if not isinstance(article, Tag):
            continue

        title = _resolve_title(article, config.item_title_selector)
        link = _resolve_link(article, config.item_link_selector, config.page_url)
        if not title or not link:
            continue

        key = _article_key(article, link)
        if key in seen:
            continue
        seen.add(key)

        date_el = article.select_one(config.item_date_selector)
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

        guid = article.get("id") or _wordpress_post_guid(article) or key
        author = _text(author_el)
        if not author and author_el is not None:
            img = author_el.select_one("img")
            if img is not None:
                author = (img.get("alt") or "").strip() or None
        image_url = _resolve_image(article, config.page_url, config.item_image_selector)
        comments_url = _href(comments_el, config.page_url)
        category = _resolve_section(article)

        items.append(
            FeedItem(
                guid=guid,
                title=title,
                link=link,
                published=published,
                author=author,
                description_html=_item_description(title, author, image_url, category),
                image_url=image_url,
                comments_url=comments_url,
                category=category,
            )
        )


def scrape_items(config: FeedConfig, *, html: Optional[str] = None) -> list[FeedItem]:
    items: list[FeedItem] = []
    seen: set[str] = set()

    if html is not None:
        _scrape_page_html(config, html, items, seen)
    else:
        for url in _listing_urls(config):
            _scrape_page_html(config, _fetch_html(url, config), items, seen)

    if config.item_sort == "date":
        items.sort(key=lambda item: item.published, reverse=True)
    return items
