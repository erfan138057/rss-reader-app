"""
core.py - موتور RSS خوان
شامل: حل DNS با DoH (دور زدن مسموم‌سازی) + فچ + پارس + ذخیره (SQLite)

بدون هیچ هزینه/سرور/ربات. همه چی محلیه.
"""
import httpx
import feedparser
import socket
import sqlite3
import time
import html
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# بخش ۱: رزولوشن DNS از طریق DoH (DNS over HTTPS)
# آدرس رو با IP ثابت سرور DoH صدا می‌زنیم تا به DNS سیستم وابسته نباشیم.
# ---------------------------------------------------------------------------

def _is_ip(h):
    try:
        socket.inet_aton(h)
        return True
    except OSError:
        return False


def doh_resolve(host, doh_ip="1.1.1.1", doh_host="cloudflare-dns.com", verify=True):
    """برگردوندن اولین آدرس IPv4 با استفاده از DoH.
    doh_ip  : آی‌پی سرور DoH (ثابته، نیاز به رزولوشن نداره)
    doh_host : هاستی که توی SNI/مدرک TLS می‌ره (برای HTTPS صحیح)
    verify   : اگه False باشه (مثلاً شبکه گواهی رو دستکاری کرده) قبولش می‌کنیم
    """
    try:
        url = f"https://{doh_ip}/dns-query"
        r = httpx.get(
            url,
            params={"name": host, "type": "A"},
            headers={"accept": "application/dns-json", "host": doh_host},
            timeout=10,
            verify=verify,
        )
        data = r.json()
        for ans in data.get("Answer", []):
            if ans.get("type") == 1:  # A record
                return ans["data"]
    except Exception as exc:
        # اگه با verify=True شکست خورد، یه بار دیگه بدون چک گواهی امتحان کن
        if verify:
            try:
                return doh_resolve(host, doh_ip, doh_host, verify=False)
            except Exception:
                pass
        print(f"⚠️ DoH نتوانست {host} را حل کند: {exc}")
    return None


# پچ کردن socket.getaddrinfo کل برنامه (فقط یک بار انجام شه)
_patched = False


def install_doh_resolver(doh_ip="1.1.1.1", doh_host="cloudflare-dns.com"):
    global _patched
    if _patched:
        return
    orig = socket.getaddrinfo

    def patched(host, *args, **kwargs):
        if _is_ip(host):
            return orig(host, *args, **kwargs)
        ip = doh_resolve(host, doh_ip, doh_host)
        if ip:
            return orig(ip, *args, **kwargs)
        # اگه DoH شکست خورد، به روش عادی (شاید DNS سیستم اوکی باشه)
        return orig(host, *args, **kwargs)

    socket.getaddrinfo = patched
    _patched = True


# ---------------------------------------------------------------------------
# بخش ۲: دیتابیس (جلوگیری از نمایش تکراری)
# ---------------------------------------------------------------------------

class Store:
    def __init__(self, db_file="rss_reader.db"):
        self.conn = sqlite3.connect(db_file)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS seen (
                   id TEXT PRIMARY KEY,
                   feed TEXT,
                   title TEXT,
                   link TEXT,
                   published TEXT
               )"""
        )
        self.conn.commit()

    def is_seen(self, item_id):
        cur = self.conn.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
        return cur.fetchone() is not None

    def mark(self, item_id, feed, title, link, published):
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO seen VALUES (?,?,?,?,?)",
                (item_id, feed, title, link, published),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]


# ---------------------------------------------------------------------------
# بخش ۳: فچ و پارس یک فید
# ---------------------------------------------------------------------------

def fetch_feed(feed_url, timeout=20):
    """برگردوندن لیست خبرها از یه فید.
    هر خبر: dict {id, title, link, summary, published}
    """
    try:
        r = httpx.get(
            feed_url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0)"},
            follow_redirects=True,
        )
        if r.status_code != 200:
            print(f"⚠️ فید {feed_url} وضعیت {r.status_code} داد")
            return []
        feed = feedparser.parse(r.content)
        items = []
        for e in feed.entries:
            items.append({
                "id": e.get("id") or e.get("link") or e.get("guid"),
                "title": html.unescape(e.get("title", "(بدون عنوان)")),
                "link": e.get("link", ""),
                "summary": html.unescape(e.get("summary", ""))[:500],
                "published": e.get("published", e.get("updated", "")),
            })
        return items
    except Exception as exc:
        print(f"❌ خطا در فچ {feed_url}: {exc}")
        return []


if __name__ == "__main__":
    # تست سریع
    install_doh_resolver()
    s = Store()
    news = fetch_feed("https://feeds.bbci.co.uk/news/rss.xml")
    for n in news[:5]:
        print("-", n["title"])
