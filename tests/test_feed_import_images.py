import unittest

from rssfeeder.feed_import import _best_image_from_html, _rss_safe_image_url


class FeedImportImageTests(unittest.TestCase):
    def test_blogger_webp_with_parentheses_becomes_jpg(self) -> None:
        raw = (
            "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEtest/"
            "s320/1439%20(0).webp"
        )
        safe = _rss_safe_image_url(raw)
        self.assertIn("/s1600/", safe)
        self.assertTrue(safe.endswith(".jpg"))
        self.assertNotIn("(", safe)

    def test_picks_parent_href_over_tiny_thumb(self) -> None:
        html = """
        <div>
          <a href="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEtest/s1439/hero%20(0).webp">
            <img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEtest/s72-h72/hero%20(0).webp" />
          </a>
        </div>
        """
        url = _best_image_from_html(html, "https://www.bandasdesenhadas.pt/")
        self.assertIsNotNone(url)
        assert url is not None
        self.assertIn("/s1600/", url)
        self.assertTrue(url.endswith(".jpg"))


if __name__ == "__main__":
    unittest.main()
