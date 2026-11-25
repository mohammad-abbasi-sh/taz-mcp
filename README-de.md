# taz-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/taz-mcp

Inoffizieller **schreibgeschützter** MCP-Server für **[taz — die tageszeitung](https://taz.de)** — eine der großen überregionalen Tageszeitungen Deutschlands (gegründet 1978, Berlin) — über den offiziellen RSS-Feed (50 Einträge, neueste zuerst) und Artikelseiten, deren Volltext aus dem JSON-LD-NewsArticle-`articleBody` gelesen wird (die serverseitig gerenderten `<article>`-Absätze sind der Fallback). Top-Schlagzeilen, Stichwortsuche, Artikel nach Autor:in, die Autor:innen des heutigen Feeds und Volltexte. Kein Schlüssel, kein Login.

> Gebaut von Mohammad Abbasi im Rahmen der „Germany MCP factory". Nicht mit der taz verbunden.

## Für KI-Agenten

In die MCP-Client-Konfiguration eintragen (stdio):

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

Oder lokal starten: `python -m taz_mcp.server` (benötigt `mcp<2`, `httpx`).

## Werkzeuge

| Werkzeug | Beschreibung |
|------|-------------|
| `taz_headlines` | Top-Schlagzeilen der taz (offizieller RSS-Feed, 50 Einträge), neueste zuerst — `limit` 1..50. Jeder Eintrag hat Titel, Artikel-Link, Teaser, Autor:in (dc:creator, sofern im Feed vorhanden), Bild-URL und Veröffentlichungszeit |
| `taz_search_news` | taz-Meldungen nach Stichwort durchsuchen (Titel + Teaser) im offiziellen RSS-Feed (50 Einträge) — `query` (z. B. „Klima"), `limit` 1..50 |
| `taz_by_author` | Neueste taz-Artikel einer Autorin / eines Autors (Feld dc:creator, z. B. „Nicole Opitz") — `author` wird als Teilstring (Groß-/Kleinschreibung egal) abgeglichen, `limit` 1..50 |
| `taz_authors` | Die Autor:innen des heutigen taz-Feeds mit der Zahl ihrer Artikel — die meisten zuerst |
| `taz_get_article` | Volltext einer taz-Artikelseite (JSON-LD-NewsArticle-`articleBody`, `<article>`-Absätze als Fallback) — `url`: eine taz.de-Artikel-URL (/<Slug>/!<Ziffern>/). Liefert Titel, Autor:in, Veröffentlichungszeit, die Rubrik aus den Breadcrumbs der Seite (z. B. „Politik > Deutschland"), Text und Wortzahl. Eine Bezahlseite liefert `paywalled: true` und nur den Teaser — der Volltext braucht ein Abo. Feed-URLs, Startseite und externe Links werden abgelehnt |
| `taz_health` | Erreichbarkeitsprüfung (ok / blocked / error) — eine höfliche Anfrage |

Beispielausgabe (`taz_headlines`, `limit` 1):

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

Hinweise:
- Der Server liest den **offiziellen RSS-Feed** — `https://taz.de/rss.xml` (50 Einträge, live geprüft am 2026-11-25). Die URL leitet per 302 auf `https://taz.de/!p4608;rss/` weiter; Weiterleitungen werden gefolgt. `/rss/` liefert 403 und `/rss` leitet auf eine Artikelseite weiter — `/rss.xml` ist der einzige Feed.
- **Keine Feeds pro Rubrik:** `/<rubrik>/rss.xml` liefert 403 für alle zehn getesteten Rubriken (politik, wirtschaft, kultur, sport, gesellschaft, deutschland, ausland, berlin, meinung, digital) — es gibt KEIN Rubriken-Werkzeug. Die Rubrik eines Artikels meldet `taz_get_article` aus der BreadcrumbList der Seite (z. B. „Politik > Deutschland").
- Der Feed enthält **keine `<category>` und kein Premium-Kennzeichen** — Einträge werden unverändert zurückgegeben. Er enthält aber ein `media:content`-Bild (taz.de/picture/..., bei allen 50 Einträgen) und eine `dc:creator`-Autorenangabe (41/50 Einträge).
- Jeder Feed-Teaser endet mit der Weiterlesen-Markierung **„ mehr..."** — sie wird aus der Beschreibung entfernt.
- **Artikeltext, ehrlich:** taz-Seiten enthalten ein echtes JSON-LD-`articleBody` (Stichprobe: 1.810–6.639 Zeichen, 238–868 Wörter bei freien Artikeln). Der Text wird whitespace-bereinigt; die `<article>`-`<p>`-Absätze sind der Fallback, wenn `articleBody` fehlt (Fotounterschriften „Foto: ..." und Byline-Fragmente werden gefiltert).
- **Paywall, ehrlich:** In den 6 am 2026-11-25 geprüften Artikeln wurde kein Bezahlartikel gefunden (alle `isAccessibleForFree: true`) — taz-Artikel sind in der Regel frei lesbar. Der Paywall-Zweig ist trotzdem defensiv implementiert: Eine Seite mit `isAccessibleForFree: false` liefert `paywalled: true` und nur den Teaser — niemals erfundenen Text.
- taz-Artikel-Links haben **kein `.html`-Suffix** (sie enden auf `/!<Ziffern>/`) — daher wird kein Suffix-Filter angewendet; jeder Feed-Eintrag wird unverändert zurückgegeben.
- Daten: öffentlicher taz-RSS-Feed und Artikelseiten — kein Schlüssel, kein Login, nur lesend.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — offline, parst den echten aufgezeichneten Feed plus eine echte Artikelseite (freier Artikel mit echtem JSON-LD-`articleBody`); der Paywall-Zweig nutzt eine kleine synthetische Seite
- `tests/test_live.py` — vorsichtige Live-Anfragen an taz.de

Tests: 24/24 grün (18 offline + 6 live, 2026-11-25).

## Lizenz

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — kostenlos für private und nicht-kommerzielle Nutzung; kommerzielle Nutzung braucht eine separate Lizenz (siehe LICENSE).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
