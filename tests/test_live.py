"""Live tests — hit the real taz.de RSS feed and article pages.
Cautious: few requests.

Run:  pytest tests/test_live.py -v
Skip: pytest -m "not live"  (or set TAZ_SKIP_LIVE=1)
"""
import json
import os
import pathlib
import sys
import unittest

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from taz_mcp import server as srv

pytestmark = pytest.mark.live
SKIP = os.environ.get("TAZ_SKIP_LIVE") == "1"


@pytest.mark.skipif(SKIP, reason="TAZ_SKIP_LIVE=1")
class TestLive(unittest.TestCase):
    def test_headlines_live(self):
        out = json.loads(srv.taz_headlines(limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(i["title"] and i["description"] for i in out["items"]))
        print(f"\nLIVE headlines: {out['count']} items, first: {out['items'][0]['title']}")

    def test_search_live(self):
        out = json.loads(srv.taz_search_news("USA", limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        print(f"\nLIVE search 'USA': {out['total_results']} hits")

    def test_by_author_live(self):
        head = json.loads(srv.taz_headlines(limit=50))
        self.assertNotIn("error", head)
        author = next(
            (i["author"] for i in head["items"] if i.get("author")), None
        )
        self.assertIsNotNone(author)
        out = json.loads(srv.taz_by_author(author, limit=3))
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(author in i["author"] for i in out["items"]))
        print(f"\nLIVE by_author {author!r}: {out['count']} items")

    def test_authors_live(self):
        out = json.loads(srv.taz_authors())
        self.assertNotIn("error", out)
        self.assertGreaterEqual(out["count"], 1)
        self.assertTrue(all(a["count"] >= 1 for a in out["authors"]))
        print(f"\nLIVE authors: {out['count']} distinct authors")

    def test_get_article_live(self):
        head = json.loads(srv.taz_headlines(limit=1))
        self.assertNotIn("error", head)
        url = head["items"][0]["link"]
        out = json.loads(srv.taz_get_article(url))
        self.assertNotIn("error", out)
        self.assertEqual(out["url"], url)
        self.assertGreater(out["word_count"], 100)
        self.assertFalse(out["paywalled"])
        self.assertTrue(out["section"])
        print(
            f"\nLIVE article: {out['title']!r} — {out['word_count']} words, "
            f"section {out['section']!r}"
        )

    def test_health_live(self):
        out = json.loads(srv.taz_health())
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["http_status"], 200)
        print(f"\nLIVE health: {out}")
