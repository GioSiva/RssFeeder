"""Fetch feed items from the WordPress REST API."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from dateutil import parser as date_parser

from rssfeeder.config import FeedConfig
from rssfeeder.scrape import FeedItem, _item_description

_STRIP_TAGS = re.compile(r"<[^>]+>")


def _parse_int_list(raw: str) -> set[int]:
    if not raw:
        return set()
    return {int(part.strip()) for part in raw.split(",") if part.strip().isdigit()}


def _parse_substrings(raw: str) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _site_origin(page_url: str) -> str:
    parsed = urlparse(page_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _parse_datetime(raw: str) -> datetime:
    parsed = date_parser.parse(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _plain_title(rendered: str) -> str:
    text = html.unescape(_STRIP_TAGS.sub("", rendered))
    return re.sub(r"\s+", " ", text).strip()


def _author_name(post: dict[str, Any]) -> str | None:
    embedded = post.get("_embedded") or {}
    authors = embedded.get("author") or []
    if not authors:
        return None
    name = authors[0].get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _featured_image_url(post: dict[str, Any]) -> str | None:
    embedded = post.get("_embedded") or {}
    media = embedded.get("wp:featuredmedia") or []
    if not media:
        return None
    item = media[0]
    url = item.get("source_url")
    if isinstance(url, str) and url and not url.startswith("data:"):
        return url
    sizes = item.get("media_details", {}).get("sizes", {})
    for key in ("large", "medium_large", "full", "medium"):
        entry = sizes.get(key)
        if isinstance(entry, dict) and entry.get("source_url"):
            return entry["source_url"]
    return None


def _category_label(post: dict[str, Any], exclude_ids: set[int]) -> str | None:
    embedded = post.get("_embedded") or {}
    for term_group in embedded.get("wp:term") or []:
        for term in term_group:
            if term.get("taxonomy") != "category":
                continue
            term_id = term.get("id")
            if term_id in exclude_ids:
                continue
            name = term.get("name")
            if isinstance(name, str) and name.strip():
                return html.unescape(name.strip())
    return "Notícias"


def _should_skip_post(
    post: dict[str, Any],
    *,
    exclude_category_ids: set[int],
    exclude_link_substrings: list[str],
) -> bool:
    post_cats = set(post.get("categories") or [])
    if post_cats & exclude_category_ids:
        return True
    link = post.get("link") or ""
    return any(part in link for part in exclude_link_substrings)


def _post_to_feed_item(post: dict[str, Any], exclude_category_ids: set[int]) -> FeedItem:
    link = post.get("link") or ""
    title = _plain_title(post.get("title", {}).get("rendered", ""))
    published = _parse_datetime(post["date"])
    author = _author_name(post)
    image_url = _featured_image_url(post)
    category = _category_label(post, exclude_category_ids)
    guid = f"post-{post.get('id', link)}"
    return FeedItem(
        guid=guid,
        title=title,
        link=link,
        published=published,
        author=author,
        description_html=_item_description(title, author, image_url, category),
        image_url=image_url,
        comments_url=None,
        category=category,
    )


def scrape_wp_json_items(config: FeedConfig) -> list[FeedItem]:
    if not config.wp_category_id:
        raise ValueError("wp_category_id is required for WordPress JSON feeds")

    origin = _site_origin(config.page_url)
    exclude_category_ids = _parse_int_list(config.exclude_category_ids)
    exclude_link_substrings = _parse_substrings(config.exclude_link_substrings)
    stop_marker = config.stop_at_link_contains.strip()

    items: list[FeedItem] = []
    headers = {"User-Agent": config.user_agent}

    for page in range(1, config.max_pages + 1):
        response = requests.get(
            f"{origin}/wp-json/wp/v2/posts",
            params={
                "categories": config.wp_category_id,
                "per_page": min(config.wp_per_page, 100),
                "page": page,
                "orderby": "date",
                "order": "desc",
                "_embed": "1",
            },
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        posts: list[dict[str, Any]] = response.json()
        if not posts:
            break

        for post in posts:
            if _should_skip_post(
                post,
                exclude_category_ids=exclude_category_ids,
                exclude_link_substrings=exclude_link_substrings,
            ):
                continue

            if not post.get("link") or not post.get("title", {}).get("rendered"):
                continue

            item = _post_to_feed_item(post, exclude_category_ids)
            items.append(item)

            if stop_marker and stop_marker in item.link:
                return items

        total_pages = int(response.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break

    return items
