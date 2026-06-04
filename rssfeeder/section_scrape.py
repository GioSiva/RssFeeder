"""Scrape posts listed under a named homepage section (e.g. «Mais lidas»)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup, Tag

from rssfeeder.config import FeedConfig
from rssfeeder.scrape import (
    FeedItem,
    _fetch_html,
    _item_description,
    _resolve_image,
    _resolve_link,
    _resolve_title,
)
from rssfeeder.wp_json import (
    _parse_int_list,
    _parse_substrings,
    _post_to_feed_item,
    _should_skip_post,
    _site_origin,
)


@dataclass(frozen=True)
class _SectionStub:
    post_id: int
    title: str
    link: str
    image_url: Optional[str]


def _normalize_heading(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _parse_headings(raw: str) -> set[str]:
    if not raw:
        return set()
    return {_normalize_heading(part) for part in raw.split(",") if part.strip()}


def _widget_heading_text(widget: Tag) -> str:
    heading = widget.select_one(".heading-title")
    if heading is None:
        return ""
    return _normalize_heading(heading.get_text())


def _elementor_top_section(widget: Tag) -> Optional[Tag]:
    node: Optional[Tag] = widget
    for _ in range(20):
        if node is None:
            return None
        classes = " ".join(node.get("class") or [])
        if "elementor-top-section" in classes:
            return node
        node = node.parent if isinstance(node.parent, Tag) else None
    return None


def _sections_from_start(soup: BeautifulSoup, start_widget: Tag) -> list[Tag]:
    sections = soup.select(".elementor-top-section")
    start_section = _elementor_top_section(start_widget)
    if start_section is None:
        return []
    for index, section in enumerate(sections):
        if section is start_section:
            return sections[index:]
    return []


def _find_start_widget(soup: BeautifulSoup, start_heading: str) -> Optional[Tag]:
    target = _normalize_heading(start_heading)
    for widget in soup.select(".elementor-widget-foxiz-heading, .elementor-widget .block-h"):
        text = _widget_heading_text(widget)
        if not text and widget.select_one(".heading-title"):
            text = _normalize_heading(widget.select_one(".heading-title").get_text())
        if text == target:
            return widget
    return None


def _link_excluded(link: str, exclude_link_substrings: list[str]) -> bool:
    return any(part in link for part in exclude_link_substrings)


def _widget_has_text(widget: Tag, needle: str) -> bool:
    if not needle:
        return False
    target = _normalize_heading(needle)
    return target in _normalize_heading(widget.get_text(" ", strip=True))


def _append_wraps(
    widget: Tag,
    config: FeedConfig,
    stubs: list[_SectionStub],
    seen_links: set[str],
    exclude_links: list[str],
) -> None:
    for wrap in widget.select(".p-wrap"):
        title = _resolve_title(wrap, config.item_title_selector)
        link = _resolve_link(wrap, config.item_link_selector, config.page_url)
        if not title or not link or link in seen_links:
            continue
        if _link_excluded(link, exclude_links):
            continue

        raw_id = wrap.get("data-pid")
        if not raw_id or not str(raw_id).isdigit():
            continue

        seen_links.add(link)
        image_url = _resolve_image(wrap, config.page_url, config.item_image_selector)
        stubs.append(
            _SectionStub(
                post_id=int(raw_id),
                title=title,
                link=link,
                image_url=image_url,
            )
        )


def _collect_section_stubs(
    config: FeedConfig,
    html: str,
) -> list[_SectionStub]:
    soup = BeautifulSoup(html, "lxml")
    start_widget = _find_start_widget(soup, config.section_start_heading)
    if start_widget is None:
        raise ValueError(f"Section heading not found: {config.section_start_heading!r}")

    sections = _sections_from_start(soup, start_widget)
    if not sections:
        raise ValueError("Could not locate Elementor sections for homepage block")

    exclude_links = _parse_substrings(config.exclude_link_substrings)
    stop_marker = config.stop_at_link_contains.strip()
    stop_at_text = config.section_stop_at_text.strip()
    skip_headings = _parse_headings(config.section_skip_headings)
    if config.section_stop_heading:
        skip_headings |= _parse_headings(config.section_stop_heading)
    hard_stop_headings = _parse_headings(config.section_hard_stop_headings)
    start_heading = _normalize_heading(config.section_start_heading)

    stubs: list[_SectionStub] = []
    seen_links: set[str] = set()
    started = False

    for section in sections:
        for widget in section.select(".elementor-widget"):
            heading_text = _widget_heading_text(widget)
            if heading_text:
                if not started:
                    if heading_text == start_heading:
                        started = True
                    continue
                if heading_text in hard_stop_headings:
                    return stubs
                if heading_text in skip_headings or heading_text.startswith("dicas e guia"):
                    continue

            if not started:
                continue

            if stop_at_text and _widget_has_text(widget, stop_at_text):
                _append_wraps(widget, config, stubs, seen_links, exclude_links)
                return stubs

            _append_wraps(widget, config, stubs, seen_links, exclude_links)

            for stub in stubs:
                if stop_marker and stop_marker in stub.link:
                    return stubs

    return stubs


def _fetch_posts_by_ids(config: FeedConfig, post_ids: list[int]) -> dict[int, dict]:
    if not post_ids:
        return {}

    origin = _site_origin(config.page_url)
    exclude_category_ids = _parse_int_list(config.exclude_category_ids)
    headers = {"User-Agent": config.user_agent}
    result: dict[int, dict] = {}

    chunk_size = 100
    for offset in range(0, len(post_ids), chunk_size):
        chunk = post_ids[offset : offset + chunk_size]
        response = requests.get(
            f"{origin}/wp-json/wp/v2/posts",
            params={
                "include": ",".join(str(pid) for pid in chunk),
                "per_page": len(chunk),
                "_embed": "1",
            },
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        for post in response.json():
            post_id = post.get("id")
            if isinstance(post_id, int):
                if _should_skip_post(
                    post,
                    exclude_category_ids=exclude_category_ids,
                    exclude_link_substrings=_parse_substrings(config.exclude_link_substrings),
                ):
                    continue
                result[post_id] = post

    return result


def scrape_section_items(config: FeedConfig, *, html: Optional[str] = None) -> list[FeedItem]:
    if not config.section_start_heading:
        raise ValueError("section_start_heading is required")

    page_html = html if html is not None else _fetch_html(config.page_url, config)
    stubs = _collect_section_stubs(config, page_html)
    if not stubs:
        return []

    posts_by_id = _fetch_posts_by_ids(config, [stub.post_id for stub in stubs])
    exclude_category_ids = _parse_int_list(config.exclude_category_ids)
    items: list[FeedItem] = []

    for stub in stubs:
        post = posts_by_id.get(stub.post_id)
        if post is None:
            continue
        item = _post_to_feed_item(post, exclude_category_ids)
        image_url = stub.image_url or item.image_url
        if image_url != item.image_url:
            item = FeedItem(
                guid=item.guid,
                title=item.title,
                link=item.link,
                published=item.published,
                author=item.author,
                description_html=_item_description(
                    item.title, item.author, image_url, item.category
                ),
                image_url=image_url,
                comments_url=item.comments_url,
                category=item.category,
            )
        items.append(item)

    return items
