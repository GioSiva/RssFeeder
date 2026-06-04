import unittest
from dataclasses import replace
from pathlib import Path

from rssfeeder.config import FeedConfig, load_preset
from rssfeeder.rss import build_rss
from rssfeeder.scrape import scrape_items

FIXTURE = Path(__file__).parent / "fixtures" / "pokebeach_snippet.html"
GI_FIXTURE = Path(__file__).parent / "fixtures" / "gameinformer_snippet.html"


class PokebeachFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = FeedConfig(
            id="pokebeach",
            title="PokeBeach",
            site_url="http://localhost:8080",
            page_url="https://www.pokebeach.com/",
            description="Test feed",
        )
        self.html = FIXTURE.read_text(encoding="utf-8")

    def test_scrape_fixture(self) -> None:
        items = scrape_items(self.config, html=self.html)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.guid, "post-320851")
        self.assertIn("Hydrapple", item.title)
        self.assertEqual(item.author, "Isaiah Cheville")
        self.assertTrue(item.link.endswith("hydrapples-rise-to-the-top"))
        self.assertIsNotNone(item.image_url)
        assert item.image_url is not None
        self.assertIn("SV07_EN_167", item.image_url)

    def test_build_rss_xml(self) -> None:
        items = scrape_items(self.config, html=self.html)
        xml = build_rss(self.config, items)
        self.assertIn("<rss", xml)
        self.assertIn("PokeBeach", xml)
        self.assertIn("Hydrapple", xml)

    def test_feed_self_link(self) -> None:
        config = replace(
            self.config,
            feed_public_path="feed/pokebeach.xml",
        )
        items = scrape_items(config, html=self.html)
        xml = build_rss(config, items)
        self.assertIn('rel="self"', xml)
        self.assertIn("http://localhost:8080/feed/pokebeach.xml", xml)


class GameInformerFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_preset("gameinformer")
        self.html = GI_FIXTURE.read_text(encoding="utf-8")

    def test_scrape_fixture(self) -> None:
        items = scrape_items(self.config, html=self.html)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.guid, "gi-126676")
        self.assertIn("Moon Studios", item.title)
        self.assertTrue(item.link.startswith("https://gameinformer.com/state-of-play/"))
        self.assertEqual(item.category, "State of Play")
        self.assertEqual(item.author, "Marcus Stewart")
        self.assertIsNotNone(item.image_url)
        assert item.image_url is not None
        self.assertIn("teaser_promoted_image_thumbnail_x2", item.image_url)
        self.assertTrue(item.image_url.startswith("https://gameinformer.com/"))


class MushuReportFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_preset("mushureport")
        self.html = (
            Path(__file__).parent / "fixtures" / "mushureport_snippet.html"
        ).read_text(encoding="utf-8")

    def test_scrape_fixture(self) -> None:
        items = scrape_items(self.config, html=self.html)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.guid, "post-18944")
        self.assertIn("Toy Story 5", item.title)
        self.assertTrue(item.link.startswith("https://mushureport.com/"))
        self.assertEqual(item.category, "News")
        self.assertEqual(item.author, "jiggy")
        self.assertIsNotNone(item.image_url)
        assert item.image_url is not None
        self.assertIn("cdn.mushureport.com", item.image_url)

    def test_lazy_loaded_image(self) -> None:
        html = (
            Path(__file__).parent / "fixtures" / "mushureport_lazy_image.html"
        ).read_text(encoding="utf-8")
        items = scrape_items(self.config, html=html)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertIsNotNone(item.image_url)
        assert item.image_url is not None
        self.assertFalse(item.image_url.startswith("data:"))
        self.assertIn("test-768x441.jpg", item.image_url)
        self.assertNotIn(".webp", item.image_url)

    def test_listing_urls_path_pagination(self) -> None:
        from rssfeeder.scrape import _listing_urls

        urls = _listing_urls(self.config)
        self.assertEqual(len(urls), 5)
        self.assertEqual(urls[0], "https://mushureport.com/category/news/")
        self.assertEqual(urls[1], "https://mushureport.com/category/news/page/2/")


class PcguiaFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_preset("pcguia")

    def test_mais_lidas_section_fixture(self) -> None:
        from unittest.mock import Mock, patch

        import rssfeeder.section_scrape as section_scrape

        html = (
            Path(__file__).parent / "fixtures" / "pcguia_mais_lidas.html"
        ).read_text(encoding="utf-8")
        posts = {
            100: {
                "id": 100,
                "date": "2026-06-04T12:00:00",
                "link": "https://www.pcguia.pt/2026/06/nzxt-aposta-forte/",
                "title": {"rendered": "NZXT aposta forte"},
                "categories": [26],
                "_embedded": {"author": [{"name": "Redação"}], "wp:featuredmedia": []},
            },
            101: {
                "id": 101,
                "date": "2026-06-04T10:00:00",
                "link": "https://www.pcguia.pt/2026/06/china-embrioes/",
                "title": {"rendered": "China envia embriões"},
                "categories": [26],
                "_embedded": {"author": [{"name": "Redação"}], "wp:featuredmedia": []},
            },
            102: {
                "id": 102,
                "date": "2026-06-04T09:00:00",
                "link": "https://www.pcguia.pt/2026/06/asrock-taichi/",
                "title": {"rendered": "ASRock celebra Taichi"},
                "categories": [26],
                "_embedded": {"author": [{"name": "Redação"}], "wp:featuredmedia": []},
            },
        }

        def fake_fetch(_config: object, post_ids: list[int]) -> dict[int, dict]:
            return {pid: posts[pid] for pid in post_ids if pid in posts}

        with patch.object(section_scrape, "_fetch_posts_by_ids", side_effect=fake_fetch):
            items = scrape_items(self.config, html=html)

        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].title, "NZXT aposta forte")
        self.assertEqual(items[1].title, "China envia embriões")
        self.assertEqual(items[2].title, "ASRock celebra Taichi")
        titles = [item.title for item in items]
        self.assertNotIn("App do Dia", titles)
        self.assertNotIn("Denon Home 200", titles)

    def test_wp_json_fixture(self) -> None:
        from unittest.mock import Mock, patch

        import rssfeeder.wp_json as wp_json

        config = replace(
            self.config,
            wp_category_id=26,
            section_start_heading="",
            stop_at_link_contains="asus-lanca-fonte-de-alimentacao-de-3000-w",
        )
        fixture = (
            Path(__file__).parent / "fixtures" / "pcguia_wp_posts.json"
        ).read_text(encoding="utf-8")
        response = Mock()
        response.json.return_value = __import__("json").loads(fixture)
        response.headers = {"X-WP-TotalPages": "1"}
        response.raise_for_status = Mock()

        with patch.object(wp_json.requests, "get", return_value=response):
            items = wp_json.scrape_wp_json_items(config)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "NZXT aposta forte na iluminação")
        self.assertIn("Asus lança fonte", items[-1].title)
        self.assertIn("asus-lanca-fonte", items[-1].link)
        self.assertEqual(items[-1].image_url, "https://www.pcguia.pt/wp-content/uploads/2026/06/ROG_Thor.jpg")
        titles = [item.title for item in items]
        self.assertNotIn("App do Dia – Exemplo", titles)
        self.assertNotIn("Nvidia revela o DLSS 4.5", titles)


class TheVergeFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_preset("theverge")

    def test_import_atom_fixture(self) -> None:
        from unittest.mock import Mock, patch

        import rssfeeder.feed_import as feed_import

        fixture = (
            Path(__file__).parent / "fixtures" / "theverge_atom_snippet.xml"
        ).read_text(encoding="utf-8")
        response = Mock()
        response.content = fixture.encode("utf-8")
        response.raise_for_status = Mock()

        with patch.object(feed_import.requests, "get", return_value=response):
            items = feed_import.import_feed_items(self.config)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.title, "Test headline from The Verge")
        self.assertEqual(item.author, "Jane Doe")
        self.assertEqual(item.category, "Tech")
        self.assertIn("platform.theverge.com", item.image_url or "")
        self.assertIn('<p><img src="https://platform.theverge.com', item.description_html)
        self.assertNotIn("<figure>", item.description_html)


if __name__ == "__main__":
    unittest.main()
