# taz-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/taz-mcp

Unofficial **read-only** MCP server for **[taz — die tageszeitung](https://taz.de)** — one of Germany's major national daily newspapers (founded 1978, Berlin) — via its official RSS feed (50 items, newest first) and article pages, whose full text is read from the JSON-LD NewsArticle `articleBody` (the server-rendered `<article>` paragraphs are the fallback). Top headlines, keyword search, stories by author, the authors in today's feed, and full article text. No key, no login.

> Built by Mohammad Abbasi as part of the "Germany MCP factory" (Sepehr-style pipeline). Not affiliated with taz.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "taz": {
      "command": "uvx",
      "args": ["taz-mcp==0.1.0"]
    }
  }
}
```

Or run locally: `python -m taz_mcp.server` (needs `mcp<2`, `httpx`).

## Tools

| Tool | Description |
|------|-------------|
| `taz_headlines` | Top taz headlines (official RSS feed, 50 items), newest first — `limit` 1..50. Every item carries a title, a per-article link, a teaser, the author (dc:creator, when the feed carries one), an image URL and publish time |
| `taz_search_news` | Search taz news by keyword (title + teaser) across the official RSS feed (50 items) — `query` (e.g. "Klima"), `limit` 1..50 |
| `taz_by_author` | Newest taz stories by one author (the feed's dc:creator field, e.g. "Nicole Opitz") — `author` matched case-insensitively as a substring, `limit` 1..50 |
| `taz_authors` | The authors in today's taz feed, with how many stories each wrote — most stories first |
| `taz_get_article` | Full text of one taz article page (JSON-LD NewsArticle `articleBody`, `<article>` paragraphs as fallback) — `url`: a taz.de article URL (/<Slug>/!<digits>/). Returns title, author, publish time, the section from the page's breadcrumbs (e.g. "Politik > Deutschland"), body text and word count. A paywalled page returns `paywalled: true` with only the teaser as body — the full text needs a subscription. Feed URLs, the home page and off-site links are refused |
| `taz_health` | Reachability probe (ok / blocked / error) — one polite request |

Example output (`taz_headlines`, `limit` 1):

```json
{"feed_title": "taz.de - taz.de", "total_results": 50, "count": 1,
 "items": [
  {"title": "Signal for Help: Hilferuf mit der Hand",
   "link": "https://taz.de/Signal-for-Help/!6232944/",
   "description": "Das „Signal for Help“ macht auf Gewalt aufmerksam – auch dort, wo Betroffene nicht offen sprechen können. Was Außenstehende wissen sollten.",
   "published": "2026-11-25T06:13:00+00:00", "author": "Nicole Opitz",
   "image_url": "https://taz.de/picture/8885377/948/Skulpturen-Irene-Melix-24--1.jpeg"},
  ...]}
```

Notes:
- The server reads the **official RSS feed** — `https://taz.de/rss.xml` (50 items, verified live 2026-11-25). The URL 302-redirects to `https://taz.de/!p4608;rss/`; redirects are followed. `/rss/` is 403 and `/rss` 302s to an article page, so `/rss.xml` is the only feed.
- **No per-section feeds exist:** `/<section>/rss.xml` 403s for all ten sections tried (politik, wirtschaft, kultur, sport, gesellschaft, deutschland, ausland, berlin, meinung, digital) — there is NO section tool. The section of one article is reported by `taz_get_article` from the page's BreadcrumbList (e.g. "Politik > Deutschland").
- The feed carries **no `<category>` and no premium flag** — items are returned as-is. It does carry a `media:content` image (taz.de/picture/..., present on all 50 items) and a `dc:creator` author (41/50 items).
- Every feed teaser ends with the read-more marker **" mehr..."** — it is stripped from the description.
- **Article text, honestly:** taz pages DO carry a real JSON-LD `articleBody` (sampled: 1,810–6,639 characters, 238–868 words on free articles). The body is whitespace-normalised; the `<article>` `<p>` tags are the fallback when `articleBody` is absent (photo captions "Foto: ..." and byline fragments filtered).
- **Paywall, honestly:** no paywalled article was found in the 6 sampled on 2026-11-25 (all `isAccessibleForFree: true`) — taz articles are generally free to read. The paywall branch is still implemented defensively: a page with `isAccessibleForFree: false` returns `paywalled: true` with only the teaser as body — never fabricated text.
- taz article links carry **no `.html` suffix** (they end in `/!<digits>/`) — so no suffix filter is applied; every feed item is returned as-is.
- Data: taz public RSS feed and article pages — no key, no login, read-only.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parses the real captured feed plus one real article page (a free article with a real JSON-LD `articleBody`); the paywalled branch uses a small synthetic page
- `tests/test_live.py` — cautious live requests against taz.de

Tests: 24/24 green (18 offline + 6 live, 2026-11-25).

## License

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — free for personal and non-commercial use; commercial use needs a separate license (see LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
