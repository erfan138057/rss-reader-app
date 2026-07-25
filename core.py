"""
core.py - موتور RSS خوان
شامل: DNS اسکنر + DoH + فچ فید + تصویر + SQLite
"""
import httpx
import feedparser
import socket
import sqlite3
import time
import html
import re
import threading
from urllib.parse import urlparse

import config

# ---------------------------------------------------------------------------
# بخش ۱: DNS over HTTPS
# ---------------------------------------------------------------------------

def _is_ip(h):
    try:
        socket.inet_aton(h)
        return True
    except OSError:
        return False


def doh_resolve(host, doh_ip, doh_host, timeout=5, verify=True):
    """رزولوشن DNS از طریق DoH. برمیگردونه IP یا None."""
    if _is_ip(host):
        return host
    try:
        r = httpx.get(
            f"https://{doh_ip}/dns-query",
            params={"name": host, "type": "A"},
            headers={"accept": "application/dns-json", "host": doh_host},
            timeout=timeout,
            verify=verify,
        )
        data = r.json()
        for ans in data.get("Answer", []):
            if ans.get("type") == 1:
                return ans["data"]
    except Exception:
        if verify:
            return doh_resolve(host, doh_ip, doh_host, timeout, verify=False)
    return None


# پچ socket برای کل برنامه
_patched = False
_doh_lock = threading.Lock()


def install_doh_resolver(doh_ip, doh_host):
    global _patched
    with _doh_lock:
        orig = socket.getaddrinfo

        def patched(host, *args, **kwargs):
            if _is_ip(host):
                return orig(host, *args, **kwargs)
            ip = doh_resolve(host, doh_ip, doh_host)
            if ip:
                return orig(ip, *args, **kwargs)
            return orig(host, *args, **kwargs)

        socket.getaddrinfo = patched
        _patched = True


# ---------------------------------------------------------------------------
# بخش ۲: DNS اسکنر
# ---------------------------------------------------------------------------

class DNSScanner:
    """
    اسکن همه سرورهای DoH:
      - latency: زمان رزولوشن یه دامنه ساده
      - filter_status: آیا سایت‌های تست رو بلاک کرده یا نه
      - working: آیا اصلاً جواب میده
    """

    TEST_DOMAIN = "www.google.com"

    def scan_server(self, server: dict, filter_sites: list[str]) -> dict:
        """اسکن یک سرور. برمیگردونه دیکشنری نتایج."""
        result = {
            "name": server["name"],
            "ip": server["ip"],
            "host": server["host"],
            "working": False,
            "latency_ms": None,
            "filters": {},   # site -> True(blocked) / False(ok) / None(error)
        }

        # تست latency
        t0 = time.monotonic()
        ip = doh_resolve(self.TEST_DOMAIN, server["ip"], server["host"], timeout=4)
        latency = (time.monotonic() - t0) * 1000

        if ip is None:
            return result

        result["working"] = True
        result["latency_ms"] = round(latency)

        # تست فیلتر هر سایت
        for site in filter_sites:
            try:
                resolved = doh_resolve(site, server["ip"], server["host"], timeout=3)
                if resolved is None:
                    result["filters"][site] = None   # خطا
                else:
                    # اگه IP به آدرس‌های بلاک‌کننده معروف ایران باشه
                    result["filters"][site] = _is_blocked_ip(resolved)
            except Exception:
                result["filters"][site] = None

        return result

    def scan_all(self, servers: list[dict], filter_sites: list[str],
                 progress_cb=None) -> list[dict]:
        """اسکن همه سرورها به صورت موازی با thread."""
        results = [None] * len(servers)
        threads = []

        def worker(i, srv):
            r = self.scan_server(srv, filter_sites)
            results[i] = r
            if progress_cb:
                progress_cb(r)

        for i, srv in enumerate(servers):
            t = threading.Thread(target=worker, args=(i, srv), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return [r for r in results if r is not None]

    def best_server(self, results: list[dict]) -> dict | None:
        """بهترین سرور = کمترین latency + بیشترین سایت‌های باز."""
        working = [r for r in results if r["working"]]
        if not working:
            return None

        def score(r):
            open_count = sum(1 for v in r["filters"].values() if v is False)
            latency = r["latency_ms"] or 9999
            # اولویت: تعداد سایت باز > latency کم
            return (-open_count, latency)

        return min(working, key=score)


# IPهای معروف سانسور/بلاک در ایران (نمونه)
_BLOCKED_IPS = {
    "10.10.34.34",   # صفحه مسدود کننده ایرانسل
    "10.10.34.35",
    "10.10.34.36",
    "178.22.122.100",
    "185.55.226.26",
    "185.55.225.25",
}

def _is_blocked_ip(ip: str) -> bool:
    return ip in _BLOCKED_IPS


# ---------------------------------------------------------------------------
# بخش ۳: دیتابیس
# ---------------------------------------------------------------------------

class Store:
    def __init__(self, db_file="rss_reader.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id        TEXT PRIMARY KEY,
                feed      TEXT,
                title     TEXT,
                link      TEXT,
                published TEXT,
                summary   TEXT,
                image_url TEXT,
                seen      INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def upsert(self, item: dict, feed_url: str):
        with self._lock:
            self.conn.execute("""
                INSERT INTO items (id, feed, title, link, published, summary, image_url, seen)
                VALUES (:id, :feed, :title, :link, :published, :summary, :image_url, 0)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    summary=excluded.summary,
                    image_url=COALESCE(excluded.image_url, items.image_url)
            """, {**item, "feed": feed_url})
            self.conn.commit()

    def mark_seen(self, item_id: str):
        with self._lock:
            self.conn.execute("UPDATE items SET seen=1 WHERE id=?", (item_id,))
            self.conn.commit()

    def get_items(self, feed_url: str | None = None) -> list[dict]:
        """همه آیتم‌ها (دیده‌شده و نشده)، جدیدترین اول."""
        with self._lock:
            if feed_url:
                cur = self.conn.execute(
                    "SELECT * FROM items WHERE feed=? ORDER BY published DESC, rowid DESC",
                    (feed_url,)
                )
            else:
                cur = self.conn.execute(
                    "SELECT * FROM items ORDER BY published DESC, rowid DESC"
                )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def update_image(self, item_id: str, image_url: str):
        with self._lock:
            self.conn.execute(
                "UPDATE items SET image_url=? WHERE id=? AND (image_url IS NULL OR image_url='')",
                (image_url, item_id)
            )
            self.conn.commit()


# ---------------------------------------------------------------------------
# بخش ۴: دریافت تصویر
# ---------------------------------------------------------------------------

def extract_image_from_feed_entry(entry) -> str | None:
    """تصویر از خود فید (media:thumbnail, enclosure, یا img در content)."""
    # media:thumbnail
    media = getattr(entry, "media_thumbnail", None)
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]

    # media:content
    media_content = getattr(entry, "media_content", None)
    if media_content and isinstance(media_content, list):
        for m in media_content:
            if m.get("medium") == "image" and m.get("url"):
                return m["url"]
            if m.get("url", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                return m["url"]

    # enclosure
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")

    # img در summary یا content
    for field in ["summary", "content"]:
        text = ""
        val = getattr(entry, field, None)
        if isinstance(val, list):
            text = " ".join(v.get("value", "") for v in val)
        elif isinstance(val, str):
            text = val
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', text, re.I)
        if m:
            url = m.group(1)
            if url.startswith("http"):
                return url

    return None


def fetch_og_image(page_url: str, timeout: int = 8) -> str | None:
    """دریافت Open Graph image از صفحه خبر."""
    try:
        r = httpx.get(
            page_url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0)"},
            follow_redirects=True,
        )
        if r.status_code != 200:
            return None
        # فقط head رو بخون برای سرعت
        html_head = r.text[:8000]
        # og:image
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html_head, re.I)
        if m:
            return m.group(1)
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html_head, re.I)
        if m:
            return m.group(1)
        # twitter:image
        m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html_head, re.I)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def fetch_image_bytes(url: str, timeout: int = 10) -> bytes | None:
    """دانلود بایت تصویر."""
    try:
        r = httpx.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        )
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            return r.content
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# بخش ۵: فچ و پارس فید
# ---------------------------------------------------------------------------

def fetch_feed(feed_url: str, timeout: int = 20) -> list[dict]:
    """دریافت و پارس فید. برمیگردونه لیست آیتم‌ها."""
    try:
        r = httpx.get(
            feed_url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0)"},
            follow_redirects=True,
        )
        if r.status_code != 200:
            print(f"⚠️ فید {feed_url} → {r.status_code}")
            return []

        feed = feedparser.parse(r.content)
        items = []
        for e in feed.entries:
            image_url = extract_image_from_feed_entry(e)
            items.append({
                "id":        e.get("id") or e.get("link") or e.get("title", ""),
                "title":     html.unescape(e.get("title", "(بدون عنوان)")),
                "link":      e.get("link", ""),
                "summary":   html.unescape(
                                 re.sub(r"<[^>]+>", "", e.get("summary", ""))
                             )[:600],
                "published": e.get("published", e.get("updated", "")),
                "image_url": image_url or "",
            })
        return items
    except Exception as exc:
        print(f"❌ خطا در فچ {feed_url}: {exc}")
        return []
