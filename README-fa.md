# taz-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/taz-mcp

سرور MCP غیررسمی و **فقط‌خواندنی** برای **[taz — دی تاگس‌تسایتونگ](https://taz.de)** — یکی از روزنامه‌های سراسری بزرگ آلمان (تأسیس ۱۹۷۸، برلین) — از طریق فید RSS رسمی (۵۰ مورد، جدیدترین اول) و صفحات مقاله که متن کامل آن‌ها از `articleBody` در JSON-LD NewsArticle خوانده می‌شود (پاراگراف‌های `<article>` رندرشده در سرور، جایگزین است). تیترهای برتر، جست‌وجوی کلیدواژه، مقاله‌ها بر اساس نویسنده، نویسندگان فید امروز و متن کامل مقاله. بدون کلید، بدون ورود.

> ساخته‌شده توسط محمد عباسی در چارچوب «کارخانه MCP آلمان». وابسته به taz نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی کلاینت MCP اضافه کنید (stdio):

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

یا به‌صورت محلی اجرا کنید: `python -m taz_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------------|
| `taz_headlines` | تیترهای برتر taz (فید RSS رسمی، ۵۰ مورد)، جدیدترین اول — `limit` از ۱ تا ۵۰. هر مورد عنوان، لینک مقاله، تیزر، نویسنده (dc:creator، وقتی در فید باشد)، آدرس تصویر و زمان انتشار دارد |
| `taz_search_news` | جست‌وجوی اخبار taz با کلیدواژه (عنوان + تیزر) در فید RSS رسمی (۵۰ مورد) — `query` (مثلاً «Klima»)، `limit` از ۱ تا ۵۰ |
| `taz_by_author` | جدیدترین مقاله‌های taz از یک نویسنده (فیلد dc:creator، مثلاً «Nicole Opitz») — `author` به‌صورت زیررشته و بدون حساسیت به بزرگی و کوچکی حروف تطبیق داده می‌شود، `limit` از ۱ تا ۵۰ |
| `taz_authors` | نویسندگان فید امروز taz با تعداد مقاله‌های هر یک — بیشترین اول |
| `taz_get_article` | متن کامل یک صفحه مقاله taz (JSON-LD NewsArticle `articleBody`، پاراگراف‌های `<article>` به‌عنوان جایگزین) — `url`: آدرس مقاله taz.de (/<Slug>/!<digits>/). عنوان، نویسنده، زمان انتشار، بخش مقاله از breadcrumb صفحه (مثلاً «Politik > Deutschland»)، متن و تعداد کلمات را برمی‌گرداند. صفحه پولی `paywalled: true` با فقط تیزر برمی‌گرداند — متن کامل نیازمند اشتراک است. آدرس‌های فید، صفحه اصلی و لینک‌های خارجی رد می‌شوند |
| `taz_health` | بررسی دسترسی (ok / blocked / error) — یک درخواست مؤدبانه |

نمونه خروجی (`taz_headlines` با `limit` برابر ۱):

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

نکته‌ها:
- سرور **فید RSS رسمی** را می‌خواند — `https://taz.de/rss.xml` (۵۰ مورد، بررسی زنده در ۲۵ نوامبر ۲۰۲۶). این آدرس با 302 به `https://taz.de/!p4608;rss/` هدایت می‌شود؛ هدایت‌ها دنبال می‌شوند. `/rss/` خطای 403 می‌دهد و `/rss` به یک صفحه مقاله هدایت می‌شود، پس `/rss.xml` تنها فید است.
- **فید جداگانه برای هر بخش وجود ندارد:** `/<section>/rss.xml` برای هر ده بخش آزمایش‌شده (politik, wirtschaft, kultur, sport, gesellschaft, deutschland, ausland, berlin, meinung, digital) خطای 403 می‌دهد — ابزار بخش وجود ندارد. بخش یک مقاله را `taz_get_article` از BreadcrumbList صفحه گزارش می‌کند (مثلاً «Politik > Deutschland»).
- فید **`<category>` و پرچم پریمیوم ندارد** — موارد همان‌طور که هستند برگردانده می‌شوند. اما تصویر `media:content` دارد (taz.de/picture/...، در هر ۵۰ مورد) و نویسنده `dc:creator` (در ۴۱ مورد از ۵۰).
- هر تیزر فید با نشان «ادامه مطلب» یعنی **« mehr...»** تمام می‌شود — این نشان از توضیح حذف می‌شود.
- **متن مقاله، صادقانه:** صفحات taz یک `articleBody` واقعی در JSON-LD دارند (نمونه: ۱٬۸۱۰ تا ۶٬۶۳۹ کاراکتر، ۲۳۸ تا ۸۶۸ کلمه در مقاله‌های رایگان). متن از نظر فاصله‌های سفید مرتب می‌شود؛ پاراگراف‌های `<p>` داخل `<article>` جایگزین‌اند وقتی `articleBody` نباشد (زیرنویس عکس‌ها «Foto: ...» و تکه‌های byline حذف می‌شوند).
- **پِی‌وال، صادقانه:** در ۶ مقاله نمونه‌برداری‌شده در ۲۵ نوامبر ۲۰۲۶ هیچ مقاله پولی پیدا نشد (همه `isAccessibleForFree: true`) — مقاله‌های taz معمولاً رایگان خوانده می‌شوند. شاخه پِی‌وال با این حال به‌صورت دفاعی پیاده شده است: صفحه‌ای با `isAccessibleForFree: false` مقدار `paywalled: true` با فقط تیزر برمی‌گرداند — هرگز متن ساختگی.
- لینک‌های مقاله taz **پسوند `.html` ندارند** (به `/!<digits>/` ختم می‌شوند) — پس فیلتر پسوند اعمال نمی‌شود؛ هر مورد فید همان‌طور که هست برگردانده می‌شود.
- داده‌ها: فید RSS عمومی و صفحات مقاله taz — بدون کلید، بدون ورود، فقط‌خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین، فید واقعی ضبط‌شده به‌علاوه یک صفحه مقاله واقعی (مقاله رایگان با `articleBody` واقعی در JSON-LD) را تجزیه می‌کند؛ شاخه پِی‌وال از یک صفحه مصنوعی کوچک استفاده می‌کند
- `tests/test_live.py` — درخواست‌های زنده محتاطانه به taz.de

تست‌ها: ۲۴ از ۲۴ سبز (۱۸ آفلاین + ۶ زنده، ۲۵ نوامبر ۲۰۲۶).

## مجوز

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — رایگان برای استفاده شخصی و غیرتجاری؛ استفاده تجاری نیازمند مجوز جداگانه است (به LICENSE مراجعه کنید).

---

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
