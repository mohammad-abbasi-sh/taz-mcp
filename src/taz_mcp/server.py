"""MCP server: unofficial read-only access to taz — die tageszeitung
(taz.de), Germany's left-liberal national daily newspaper — via its
official RSS feed (50 items, newest first) and article pages (full
text from the JSON-LD NewsArticle articleBody; the server-rendered
<article> paragraphs are the fallback). No key, no login."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import domain as _dom
from . import http as _http

INSTRUCTIONS = """\
Unofficial read-only MCP server for taz — die tageszeitung
(taz.de), Germany's left-liberal national daily newspaper — via
its official RSS feed (no key, no login) and article pages. The
feed (50 items, newest first, with teaser, author and image),
keyword search across the feed, stories by author, the authors
in today's feed, and full article text (the JSON-LD NewsArticle
articleBody — 1,800–6,600 characters sampled — with the
server-rendered <article> paragraphs as fallback). No per-section
feeds exist on taz.de, so there is no section tool; the section
of one article (e.g. "Politik > Deutschland") is reported by
taz_get_article from the page's breadcrumbs. taz articles are
generally free to read; a paywalled page is reported as
paywalled=true with the teaser only, never fabricated text.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · \
https://mabbasi.ir — Germany MCP factory.\
"""


_SOURCE = "taz.de"
_DISCLAIMER = "Unofficial read-only data from taz's public RSS feed and article pages; verify on the site before acting on it."


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


mcp = FastMCP("taz-mcp", instructions=INSTRUCTIONS)


def _feed(limit: int) -> dict:
    """Fetch the taz RSS feed and return its items, newest first, capped."""
    parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
    items = parsed["items"][:limit]
    return {
        "feed_title": parsed["feed_title"],
        "total_results": parsed["count"],
        "count": len(items),
        "items": items,
    }


@mcp.tool()
def taz_headlines(limit: int = 10) -> str:
    """Top taz headlines (official RSS feed, 50 items), newest first.
limit: 1..50 (default 10). Every item carries a title, a per-article
link for taz_get_article, a teaser (description), the author
(dc:creator, when the feed carries one), an image URL and publish
time."""
    try:
        lim = _dom.validate_limit(limit)
        out = _feed(lim)
    except (_http.TazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def taz_search_news(query: str, limit: int = 10) -> str:
    """Search taz news by keyword (title + teaser) across the official
RSS feed (50 items). query: free text, e.g. "Klima" or "Bundesliga".
limit: 1..50 (default 10). Newest first, de-duplicated by link."""
    try:
        if not (query or "").strip():
            return _ok({"error": "query must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.search_items(parsed["items"], query.strip())
        out = {
            "query": query.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.TazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def taz_by_author(author: str, limit: int = 10) -> str:
    """Newest taz stories by one author (the feed's dc:creator field,
e.g. "Nicole Opitz" or "Robert Misik"). author: free text, matched
case-insensitively as a substring. limit: 1..50 (default 10).
Items carry title, link (a per-article URL for taz_get_article),
teaser, author, image URL and publish time."""
    try:
        if not (author or "").strip():
            return _ok({"error": "author must not be empty"})
        lim = _dom.validate_limit(limit)
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        found = _dom.items_by_author(parsed["items"], author.strip())
        out = {
            "author": author.strip(),
            "total_results": len(found),
            "count": min(lim, len(found)),
            "items": found[:lim],
        }
    except (_http.TazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def taz_authors() -> str:
    """The authors in today's taz feed, with how many stories each
wrote — most stories first. Items without an author in the feed
are not counted. Use taz_by_author to read one author's stories."""
    try:
        parsed = _dom.parse_rss(_http.fetch_feed(_dom.HEADLINES_FEED))
        authors = _dom.authors_with_counts(parsed["items"])
        out = {
            "total_results": len(authors),
            "count": len(authors),
            "authors": authors,
        }
    except (_http.TazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def taz_get_article(url: str) -> str:
    """Full text of one taz article page (the JSON-LD NewsArticle
articleBody, with the server-rendered <article> paragraphs as
fallback). url: a taz.de article URL, e.g. from taz_headlines
(/<Slug>/!<digits>/). Returns title, author, publish time, the
section from the page's breadcrumbs (e.g. "Politik >
Deutschland"), the body text and its word count. A paywalled page
returns paywalled=true with only the teaser as body — the full
text needs a subscription. Feed URLs, the home page and off-site
links are refused. Nothing is ever fabricated."""
    try:
        if not (url or "").strip():
            return _ok({"error": "url must not be empty"})
        url = url.strip()
        article = _dom.parse_article(_http.fetch_article(url))
        paywalled = article["paywalled"]
        note = ""
        if paywalled:
            note = (
                "This article is paywalled: only the teaser is "
                "available; the full text needs a subscription."
            )
        elif article["teaser_only"]:
            note = (
                "Only the teaser is available for this item; the teaser "
                "is the whole freely available text."
            )
        out = {
            "url": url,
            "title": article["title"],
            "author": article["author"],
            "published": article["published"],
            "section": article["section"],
            "kind": article["kind"],
            "paywalled": paywalled,
            "teaser_only": article["teaser_only"],
            "word_count": article["word_count"],
            "body": article["body"],
            "description": article["description"],
            "note": note,
        }
    except (_http.TazError, ValueError) as e:
        return _err(e)
    return _ok(out)


@mcp.tool()
def taz_health() -> str:
    """Check whether the taz RSS feed is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    sys.exit(main())
