"""Domain logic: shape taz.de's official RSS feed and article pages
into compact dicts (stdlib only).

Data source: the official taz RSS feed (no key, no login) —
https://taz.de/rss.xml (50 items, newest first) — plus article
pages, whose full text lives in the JSON-LD NewsArticle
"articleBody" (the server-rendered <article> paragraphs are the
fallback).

Honest limitations (verified live 2026-11-25):
- /rss.xml 302-redirects to https://taz.de/!p4608;rss/ — the feed
  URL is fetched with redirects followed. /rss/ is 403 and /rss
  302s to an article page, so the real feed is /rss.xml only.
- NO per-section feeds exist: /<section>/rss.xml 403s for all ten
  sections tried (politik, wirtschaft, kultur, sport,
  gesellschaft, deutschland, ausland, berlin, meinung, digital)
  — there is NO section tool. The section of one article is
  reported by taz_get_article from the page's BreadcrumbList
  (e.g. "Politik > Deutschland").
- The feed carries NO <category> and NO premium flag — items are
  returned as-is. It does carry a media:content image
  (taz.de/picture/...) and a dc:creator author on 41/50 items.
- Article body: the JSON-LD NewsArticle articleBody IS the full
  text (sampled: 1,810–6,639 chars, 238–868 words, free articles
  with isAccessibleForFree=true). The <article> <p> tags are the
  fallback when articleBody is absent. Caption lines ("Foto: ...")
  and byline fragments are filtered from the fallback.
- PAYWALL: no paywalled article was found in the 6 sampled
  (all isAccessibleForFree=true) — taz articles are generally
  free to read. The paywall branch is still implemented
  defensively: a page with isAccessibleForFree=false returns
  paywalled=true with only the teaser as body, never fabricated
  text.
- The feed's <description> is the teaser (~150-250 chars).
- Article links are https://taz.de/<Slug>/!<digits>/ (no .html
  suffix) — so no suffix filter is applied.
"""
from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

BASE = "https://taz.de"
HEADLINES_FEED = f"{BASE}/rss.xml"

_MEDIA_NS = "http://search.yahoo.com/mrss/"
_DC_NS = "http://purl.org/dc/elements/1.1/"


def validate_limit(limit: int) -> int:
    """Clamp/validate the page size (the feed carries 50 items)."""
    if not 1 <= limit <= 50:
        raise ValueError(f"limit out of range: {limit} (expected 1..50)")
    return limit


def _text(elem, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return html.unescape(child.text).strip()


def _iso(date_text: str) -> str | None:
    if not date_text:
        return None
    text = date_text.strip()
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(raw: str) -> str:
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _published(item: ET.Element) -> str | None:
    """pubDate (RSS 2.0) or dc:date — matched by local name."""
    for child in item:
        local = child.tag.rsplit("}", 1)[-1]
        if local in ("pubDate", "date") and child.text:
            return _iso(child.text)
    return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def compact_item(item: ET.Element) -> dict | None:
    """One RSS 2.0 <item>: title, link, teaser, publish time, author
    (dc:creator) and image URL (first image/jpeg media:content).

    Returns None for off-site links (none seen in the feed, but the
    guard keeps the contract explicit).
    """
    link = _text(item, "link")
    if not link.startswith("https://taz.de/"):
        return None
    title = _text(item, "title")
    description = _strip_tags(_text(item, "description"))
    # Every taz teaser ends with the "read more" marker " mehr...".
    if description.endswith(" mehr..."):
        description = description[: -len(" mehr...")].strip()
    if not title:
        title = description
    author = ""
    image_url = None
    for child in item:
        local = _local(child.tag)
        if local == "creator" and child.text:
            author = html.unescape(child.text).strip()
        elif local == "content":
            mime = (child.get("type") or "").strip()
            url = (child.get("url") or "").strip()
            if mime == "image/jpeg" and url and image_url is None:
                image_url = html.unescape(url)
    return {
        "title": title,
        "link": link,
        "description": description,
        "published": _published(item),
        "author": author,
        "image_url": image_url,
    }


def parse_rss(xml_text: str) -> dict:
    """Parse the taz RSS 2.0 feed into {feed_title, count, items}.

    Raises ValueError on malformed XML or a non-RSS document.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"invalid RSS XML: {e}") from e
    channel = root.find("channel")
    if channel is None:
        raise ValueError("unexpected RSS shape: no <channel> element")
    items = []
    for it in channel.findall("item"):
        compacted = compact_item(it)
        if compacted is not None:
            items.append(compacted)
    return {
        "feed_title": _text(channel, "title"),
        "count": len(items),
        "items": items,
    }


_LD_JSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    re.S | re.I,
)
_ARTICLE_RE = re.compile(r"<article[^>]*>(.*?)</article>", re.S | re.I)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_OG_DESC_RE = re.compile(
    r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',
    re.S | re.I,
)


def _author_name(raw) -> str:
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        return str(raw.get("name") or "").strip()
    if isinstance(raw, list):
        names = [_author_name(a) for a in raw]
        return ", ".join(n for n in names if n)
    return ""


def _ld_blocks(html_text: str) -> list:
    """JSON-LD blocks (a block may be a single object or a list)."""
    blocks: list[dict] = []
    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            blocks.append(data)
        elif isinstance(data, list):
            blocks.extend(b for b in data if isinstance(b, dict))
    return blocks


def _page_title(html_text: str) -> str:
    match = _TITLE_RE.search(html_text)
    if not match:
        return ""
    title = _strip_tags(match.group(1))
    return re.sub(r"\s*\|\s*taz\.de\s*$", "", title, flags=re.I)


def _section_from_breadcrumbs(blocks: list) -> str:
    """Top section of the article from the BreadcrumbList block
    (position 2, e.g. "Politik"); "" when absent."""
    for block in blocks:
        if block.get("@type") != "BreadcrumbList":
            continue
        elements = block.get("itemListElement") or []
        names = []
        for el in elements:
            if isinstance(el, dict) and el.get("position", 0) > 1:
                name = str(el.get("name") or "").strip()
                if name:
                    names.append(name)
        # Last element is the article itself — drop it.
        if len(names) > 1:
            names = names[:-1]
        return " > ".join(names)
    return ""


def _clean_body_text(raw: str) -> str:
    """Normalise a JSON-LD articleBody: collapse runs of spaces,
    keep paragraph breaks, strip leading/trailing whitespace."""
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.splitlines()]
    paras: list[str] = []
    buf = ""
    for ln in lines:
        if ln:
            buf = f"{buf} {ln}".strip() if buf else ln
        elif buf:
            paras.append(buf)
            buf = ""
    if buf:
        paras.append(buf)
    return "\n\n".join(paras).strip()


def _ssr_body(
    html_text: str, title: str, description: str, author: str = ""
) -> str:
    """Body text from the server-rendered <article> paragraphs
    (fallback when the JSON-LD articleBody is absent).

    Filters out photo captions ("Foto: ..."), byline fragments
    (bare author-name tokens), repeats of the title / description,
    and de-duplicates identical paragraphs. Raises ValueError when
    no usable body paragraphs are found.
    """
    match = _ARTICLE_RE.search(html_text)
    if not match:
        raise ValueError(
            "no article text found on this page (no <article> body) — "
            "the page may be JS-rendered or an error page"
        )
    author_tokens = {
        t.casefold() for t in re.split(r"[^A-Za-zÀ-ÿ-]+", author) if t
    }
    paras: list[str] = []
    seen: set[str] = set()
    for raw in _P_RE.findall(match.group(1)):
        text = _strip_tags(raw)
        if not text:
            continue
        if text.startswith("Foto:"):
            continue  # photo caption, not article text
        if " " not in text and text.casefold() in author_tokens:
            continue  # byline fragment: a bare author-name token
        if title and text == title:
            continue  # header paragraph: the title again
        if description and text == description:
            continue  # teaser paragraph: the description again
        if text in seen:
            continue  # repeated paragraph (teaser echo)
        seen.add(text)
        paras.append(text)
    body = "\n\n".join(paras).strip()
    if not body:
        raise ValueError(
            "no article text found on this page (the <article> body is "
            "empty after filtering)"
        )
    return body


def parse_article(html_text: str) -> dict:
    """Extract the article from a taz.de page.

    Metadata comes from the JSON-LD NewsArticle block (headline,
    description, author list, datePublished, isAccessibleForFree)
    and the BreadcrumbList block (section); the body comes from the
    JSON-LD articleBody, falling back to the server-rendered
    <article> paragraphs. A paywalled page
    (isAccessibleForFree=false) returns paywalled=true with only
    the teaser as body — never fabricated text. Returns {title,
    description, body, author, published, section, word_count,
    teaser_only, paywalled, kind}. Raises ValueError when no usable
    text is found.
    """
    blocks = _ld_blocks(html_text)
    article_block = None
    for block in blocks:
        if block.get("@type") in ("NewsArticle", "Article"):
            article_block = block
            break

    title = _page_title(html_text)
    description = ""
    og = _OG_DESC_RE.search(html_text)
    if og:
        description = html.unescape(og.group(1)).strip()

    paywalled = False
    body = ""
    if article_block is not None:
        free = article_block.get("isAccessibleForFree")
        if free is not None:
            paywalled = not bool(free)
        title = (
            _strip_tags(str(article_block.get("headline") or "")) or title
        )
        description = description or _strip_tags(
            str(article_block.get("description") or "")
        )
        if not paywalled:
            body = _clean_body_text(
                str(article_block.get("articleBody") or "")
            )

    author = ""
    published = None
    if article_block is not None:
        author = _author_name(article_block.get("author"))
        published = str(article_block.get("datePublished") or "") or None

    section = _section_from_breadcrumbs(blocks)

    if paywalled:
        # Only the teaser is available — never the full text.
        body = description
        if not body:
            raise ValueError(
                "no article text found on this page (paywalled and no "
                "teaser available)"
            )
    elif not body:
        body = _ssr_body(html_text, title, description, author)

    teaser_only = paywalled or (bool(body) and body == description)
    return {
        "title": title,
        "description": description,
        "body": body,
        "author": author,
        "published": published,
        "section": section,
        "word_count": len(body.split()),
        "teaser_only": teaser_only,
        "paywalled": paywalled,
        "kind": "article",
    }


def search_items(items: list, query: str) -> list:
    """Case-insensitive substring match over title + description."""
    q = (query or "").strip().casefold()
    if not q:
        raise ValueError("query must not be empty")
    return [
        it for it in items
        if q in (it.get("title") or "").casefold()
        or q in (it.get("description") or "").casefold()
    ]


def items_by_author(items: list, author: str) -> list:
    """Case-insensitive substring match over the dc:creator author."""
    q = (author or "").strip().casefold()
    if not q:
        raise ValueError("author must not be empty")
    return [
        it for it in items
        if q in (it.get("author") or "").casefold()
    ]


def authors_with_counts(items: list) -> list:
    """Distinct authors in the feed, with their story counts,
    most stories first (items without an author are skipped)."""
    counts: dict[str, int] = {}
    for it in items:
        name = (it.get("author") or "").strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return [
        {"author": name, "count": n}
        for name, n in sorted(
            counts.items(), key=lambda kv: (-kv[1], kv[0])
        )
    ]


def dedupe_sort(items: list) -> list:
    """De-duplicate by link, newest first (empty publish time sorts last)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for it in items:
        if it["link"] in seen:
            continue
        seen.add(it["link"])
        unique.append(it)
    unique.sort(key=lambda it: it.get("published") or "", reverse=True)
    return unique
