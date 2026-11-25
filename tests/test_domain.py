"""Offline tests — parse the real captured taz.de RSS feed and one
real article page (a free NewsArticle with a real JSON-LD
articleBody), no network. The paywalled branch is tested with a
small synthetic page (no paywalled taz article was found in the
6 sampled on 2026-11-25 — taz articles are generally free)."""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from taz_mcp import domain as dom
from taz_mcp import http as http_mod

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


_PAYWALLED_HTML = """<!DOCTYPE html><html><head><title>Test: Bezahlartikel | taz.de</title>
<meta property="og:description" content="Nur der Teaser ist frei lesbar.">
<script type="application/ld+json">{"@context": "https://schema.org",
"@type": "NewsArticle", "headline": "Test: Bezahlartikel",
"description": "Nur der Teaser ist frei lesbar.",
"isAccessibleForFree": false,
"articleBody": "Der volle Text steht nur Abonnenten zur Verfügung.",
"author": [{"@type": "Person", "name": "Max Muster"}],
"datePublished": "2026-11-25T08:00:00+01:00"}</script>
<script type="application/ld+json">{"@context": "https://schema.org",
"@type": "BreadcrumbList", "itemListElement": [
{"@type": "ListItem", "position": 1, "name": "Startseite"},
{"@type": "ListItem", "position": 2, "name": "Wirtschaft"},
{"@type": "ListItem", "position": 3, "name": "Test: Bezahlartikel"}]}</script>
</head><body><article><p>Nur der Teaser ist frei lesbar.</p>
<p>Der volle Text steht nur Abonnenten zur Verfügung.</p></article>
</body></html>"""


class TestHeadlinesFeed:
    def test_main_shape(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert parsed["feed_title"] == "taz.de - taz.de"
        assert parsed["count"] == 50
        assert len(parsed["items"]) == 50

    def test_main_first_item(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        first = parsed["items"][0]
        assert first["title"] == "Signal for Help: Hilferuf mit der Hand"
        assert first["link"] == "https://taz.de/Signal-for-Help/!6232944/"
        assert first["description"].startswith(
            "Das „Signal for Help“ macht auf Gewalt aufmerksam"
        )
        # The trailing " mehr..." read-more marker is stripped.
        assert not first["description"].endswith("mehr...")
        # pubDate "07:13:00 +0100" is 06:13:00 UTC.
        assert first["published"] == "2026-11-25T06:13:00+00:00"
        assert first["author"] == "Nicole Opitz"
        assert first["image_url"] == (
            "https://taz.de/picture/8885377/948/"
            "Skulpturen-Irene-Melix-24--1.jpeg"
        )

    def test_main_items_all_have_title_description_image(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert all(i["title"] and i["description"] for i in parsed["items"])
        assert all(i["image_url"] for i in parsed["items"])
        assert all(
            i["link"].startswith("https://taz.de/") for i in parsed["items"]
        )

    def test_author_coverage(self):
        # 41 of the 50 items carry a dc:creator author.
        parsed = dom.parse_rss(_read("headlines.xml"))
        assert sum(1 for i in parsed["items"] if i["author"]) == 41
        assert sum(1 for i in parsed["items"] if not i["author"]) == 9


class TestArticle:
    def test_free_article(self):
        art = dom.parse_article(_read("article-free.html"))
        assert art["kind"] == "article"
        assert art["title"] == "Signal for Help: Hilferuf mit der Hand"
        assert art["author"] == "Nicole Opitz"
        assert art["published"] == "2026-11-25T07:13:00+01:00"
        assert art["section"] == "Politik > Deutschland"
        assert art["word_count"] == 440
        assert art["paywalled"] is False
        assert art["teaser_only"] is False

    def test_free_article_body_is_json_ld(self):
        # taz pages DO carry a real JSON-LD articleBody — it is the
        # body (the SSR <article> paragraphs are only the fallback).
        art = dom.parse_article(_read("article-free.html"))
        assert art["body"].startswith(
            "Fünf Finger, die ausgestreckt werden, dann wird der "
            "Daumen erst eingeknickt"
        )
        assert "Signal for Help" in art["body"]
        assert art["description"].startswith(
            "Das „Signal for Help“ macht auf Gewalt aufmerksam"
        )

    def test_free_article_body_has_no_photo_captions(self):
        art = dom.parse_article(_read("article-free.html"))
        assert "Foto:" not in art["body"]

    def test_paywalled_article_returns_teaser_only(self):
        art = dom.parse_article(_PAYWALLED_HTML)
        assert art["kind"] == "article"
        assert art["title"] == "Test: Bezahlartikel"
        assert art["author"] == "Max Muster"
        assert art["published"] == "2026-11-25T08:00:00+01:00"
        assert art["section"] == "Wirtschaft"
        assert art["paywalled"] is True
        assert art["teaser_only"] is True
        # Only the teaser is exposed — never the full text.
        assert art["body"] == "Nur der Teaser ist frei lesbar."
        assert "Abonnenten" not in art["body"]


class TestValidators:
    def test_limit(self):
        assert dom.validate_limit(1) == 1
        assert dom.validate_limit(50) == 50
        with pytest.raises(ValueError):
            dom.validate_limit(0)
        with pytest.raises(ValueError):
            dom.validate_limit(51)


class TestSearchAuthorAndDedupe:
    def test_search_items(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        found = dom.search_items(parsed["items"], "USA")
        assert len(found) == 5
        assert dom.search_items(parsed["items"], "usa") == found
        with pytest.raises(ValueError):
            dom.search_items(parsed["items"], "   ")

    def test_items_by_author(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        found = dom.items_by_author(parsed["items"], "Opitz")
        assert len(found) == 1
        assert found[0]["author"] == "Nicole Opitz"
        assert dom.items_by_author(parsed["items"], "opitz") == found
        assert dom.items_by_author(parsed["items"], "Niemand") == []
        with pytest.raises(ValueError):
            dom.items_by_author(parsed["items"], "   ")

    def test_authors_with_counts(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        authors = dom.authors_with_counts(parsed["items"])
        assert len(authors) == 39
        assert authors[0]["count"] == 2
        assert {"author": "Christian Rath", "count": 2} in authors
        assert {"author": "Nicole Opitz", "count": 1} in authors
        counts = [a["count"] for a in authors]
        assert counts == sorted(counts, reverse=True)

    def test_dedupe_sort(self):
        parsed = dom.parse_rss(_read("headlines.xml"))
        doubled = parsed["items"] + parsed["items"][:5]
        out = dom.dedupe_sort(doubled)
        assert len(out) == 50
        pubs = [i["published"] for i in out]
        assert pubs == sorted(pubs, reverse=True)


class TestFeedGuards:
    def test_parse_rss_rejects_garbage(self):
        with pytest.raises(ValueError):
            dom.parse_rss("<html><body>not rss</body></html>")

    def test_fetch_article_refuses_feed_urls(self):
        with pytest.raises(http_mod.TazError):
            http_mod.fetch_article("https://taz.de/rss.xml")
        with pytest.raises(http_mod.TazError):
            http_mod.fetch_article("https://taz.de/")

    def test_fetch_article_refuses_other_hosts(self):
        with pytest.raises(http_mod.TazError):
            http_mod.fetch_article(
                "https://www.spiegel.de/politik/deutschland/afd-100.html"
            )
        with pytest.raises(http_mod.TazError):
            http_mod.fetch_article(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )

    def test_fetch_feed_refuses_non_feed_urls(self):
        with pytest.raises(http_mod.TazError):
            http_mod.fetch_feed("https://taz.de/politik/")
        with pytest.raises(http_mod.TazError):
            http_mod.fetch_feed("https://taz.de/Signal-for-Help/!6232944/")


class TestServerEnvelope:
    def test_tools_return_json_envelope(self):
        # Offline: the tools hit the network, so only the error path
        # is exercised here — but the envelope shape is the same.
        from taz_mcp import server as srv

        out = json.loads(srv.taz_headlines(51))
        assert "error" in out
        assert out["source"] == "taz.de"
        assert "fetched_at" in out
