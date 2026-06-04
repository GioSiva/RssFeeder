import unittest
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


class GameInformerFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_preset("gameinformer")
        self.html = GI_FIXTURE.read_text(encoding="utf-8")

    def test_scrape_fixture(self) -> None:
        items = scrape_items(self.config, html=self.html)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.guid, "gi-126684")
        self.assertIn("Control Resonant", item.title)
        self.assertTrue(item.link.startswith("https://gameinformer.com/"))
        self.assertIsNotNone(item.image_url)
        assert item.image_url is not None
        self.assertTrue(item.image_url.startswith("https://gameinformer.com/"))


if __name__ == "__main__":
    unittest.main()
