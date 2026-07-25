"""
core.py - موتور RSS خوان
شامل: DNS اسکنر + DoH + فچ فید + تصویر + SQLite + وضعیت اینترنت + لاگ
"""
import httpx
import feedparser
import socket
import sqlite3
import time
import html
import re
import threading
import logging
import sys
from urllib.parse import urlparse
from datetime import datetime

import config

# ---------------------------------------------------------------------------
# لاگ مرکزی
# ---------------------------------------------------------------------------

class AppLogger:
    """لاگ در حافظه + فایل + callback برای UI."""
    def __init__(self, max_lines: int = 500):
        self._lines: list[str] = []
        self._max = max_lines
        self._lock = threading.Lock()
        self._callbacks: list = []
        # لاگر استاندارد
        self.logger = logging.getLogger("RSSReader")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                                datefmt="%H:%M:%S"))
        self.logger.addHandler(handler)

    def _write(self, level: str, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {level}  {msg}"
        with self._lock:
            self._lines.append(line)
            if len(self._lines) > self._max:
                self._lines = self._lines[-self._max:]
        for cb in self._callbacks:
            try:
                cb(line)
            except Exception:
                pass

    def add_callback(self, cb):
        self._callbacks.append(cb)

    def remove_callback(self, cb):
        self._callbacks = [c for c in self._callbacks if c is not cb]

    def info(self, msg):
        self.logger.info(msg)
        self._write("INFO ", msg)

    def warning(self, msg):
        self.logger.warning(msg)
        self._write("WARN ", msg)

    def error(self, msg):
        self.logger.error(msg)
        self._write("ERROR", msg)

    def debug(self, msg):
        self.logger.debug(msg)
        self._write("DEBUG", msg)

    def get_lines(self) -> list[str]:
        with self._lock:
            return list(self._lines)

LOG = AppLogger()

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
    except Exception as e:
        if verify:
            return doh_resolve(host, doh_ip, doh_host, timeout, verify=False)
        LOG.debug(f"DoH fail {host}@{doh_ip}: {e}")
    return None


_doh_lock = threading.Lock()

def install_doh_resolver(doh_ip, doh_host):
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
    LOG.info(f"DoH فعال: {doh_host} ({doh_ip})")

# ---------------------------------------------------------------------------
# بخش ۲: DNS اسکنر
# ---------------------------------------------------------------------------

_BLOCKED_IPS = {
    "10.10.34.34", "10.10.34.35", "10.10.34.36",
    "178.22.122.100", "185.55.226.26", "185.55.225.25",
}

def _is_blocked_ip(ip: str) -> bool:
    return ip in _BLOCKED_IPS


class DNSScanner:
    TEST_DOMAIN = "www.google.com"

    def scan_server(self, server: dict, filter_sites: list) -> dict:
        result = {
            "name": server["name"], "ip": server["ip"], "host": server["host"],
            "working": False, "latency_ms": None, "filters": {},
        }
        t0 = time.monotonic()
        ip = doh_resolve(self.TEST_DOMAIN, server["ip"], server["host"], timeout=4)
        latency = (time.monotonic() - t0) * 1000
        if ip is None:
            LOG.warning(f"DNS {server['name']} پاسخ نداد")
            return result
        result["working"] = True
        result["latency_ms"] = round(latency)
        LOG.info(f"DNS {server['name']} → {latency:.0f}ms")
        for site in filter_sites:
            try:
                resolved = doh_resolve(site, server["ip"], server["host"], timeout=3)
                result["filters"][site] = _is_blocked_ip(resolved) if resolved else None
            except Exception:
                result["filters"][site] = None
        return result

    def scan_all(self, servers, filter_sites, progress_cb=None) -> list:
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

    def best_server(self, results: list) -> dict | None:
        working = [r for r in results if r["working"]]
        if not working:
            return None
        def score(r):
            open_count = sum(1 for v in r["filters"].values() if v is False)
            return (-open_count, r["latency_ms"] or 9999)
        return min(working, key=score)

# ---------------------------------------------------------------------------
# بخش ۳: وضعیت اینترنت ایران
# ---------------------------------------------------------------------------

class InternetMonitor:
    """
    هر N ثانیه وضعیت اتصال اینترنت ایران رو چک میکنه.
    از Cloudflare Radar API استفاده میکنه (رایگان، بدون نیاز به key).
    fallback: تست مستقیم ping به چند سرور.
    """
    RADAR_URL = "https://radar.cloudflare.com/api/v4/radar/quality/iqi/summary"
    PING_HOSTS = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]

    def __init__(self, interval: int = 60, on_update=None):
        self.interval = interval
        self.on_update = on_update
        self._running = False
        self._last: dict = {"percent": None, "label": "در حال بررسی...", "color": "gray"}

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            result = self._check()
            self._last = result
            if self.on_update:
                self.on_update(result)
            time.sleep(self.interval)

    def _check(self) -> dict:
        # روش ۱: تست ping ساده به چند سرور معتبر
        ok = 0
        total = len(self.PING_HOSTS)
        latencies = []
        for host in self.PING_HOSTS:
            try:
                t0 = time.monotonic()
                s = socket.create_connection((host, 443), timeout=4)
                s.close()
                latencies.append((time.monotonic() - t0) * 1000)
                ok += 1
            except Exception:
                pass

        percent = round((ok / total) * 100)
        avg_ms = round(sum(latencies) / len(latencies)) if latencies else None

        if percent >= 80:
            label = f"اینترنت: خوب ({avg_ms}ms)" if avg_ms else "اینترنت: خوب"
            color = "#43A047"
        elif percent >= 40:
            label = f"اینترنت: متوسط ({percent}%)"
            color = "#FB8C00"
        else:
            label = f"اینترنت: ضعیف ({percent}%)"
            color = "#E53935"

        LOG.info(f"وضعیت اینترنت: {percent}% — {label}")
        return {"percent": percent, "label": label, "color": color, "latency_ms": avg_ms}

    @property
    def last(self):
        return self._last

# ---------------------------------------------------------------------------
# بخش ۴: دیتابیس
# ---------------------------------------------------------------------------

class Store:
    def __init__(self, db_file="rss_reader.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id        TEXT PRIMARY KEY,
                feed      TEXT,
                title     TEXT,
                link      TEXT,
                published TEXT,
                summary   TEXT,
                image_url TEXT,
                seen      INTEGER DEFAULT 0,
                click_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS feeds (
                url       TEXT PRIMARY KEY,
                title     TEXT,
                pinned    INTEGER DEFAULT 0,
                added_at  TEXT
            );
        """)
        self.conn.commit()
        LOG.info(f"دیتابیس باز شد: {db_file}")

    # ---- آیتم‌ها ----
    def upsert(self, item: dict, feed_url: str):
        with self._lock:
            self.conn.execute("""
                INSERT INTO items (id, feed, title, link, published, summary, image_url, seen, click_count)
                VALUES (:id, :feed, :title, :link, :published, :summary, :image_url, 0, 0)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    summary=excluded.summary,
                    image_url=COALESCE(excluded.image_url, items.image_url)
            """, {**item, "feed": feed_url})
            self.conn.commit()

    def mark_seen(self, item_id: str):
        with self._lock:
            self.conn.execute(
                "UPDATE items SET seen=1, click_count=click_count+1 WHERE id=?", (item_id,))
            self.conn.commit()

    def get_items(self, feed_url=None, sort="newest") -> list:
        order = {
            "newest":  "published DESC, rowid DESC",
            "oldest":  "published ASC, rowid ASC",
        }.get(sort, "published DESC, rowid DESC")
        with self._lock:
            if feed_url:
                cur = self.conn.execute(
                    f"SELECT * FROM items WHERE feed=? ORDER BY {order}", (feed_url,))
            else:
                cur = self.conn.execute(f"SELECT * FROM items ORDER BY {order}")
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def update_image(self, item_id: str, image_url: str):
        with self._lock:
            self.conn.execute(
                "UPDATE items SET image_url=? WHERE id=? AND (image_url IS NULL OR image_url='')",
                (image_url, item_id))
            self.conn.commit()

    # ---- فیدها ----
    def add_feed(self, url: str, title: str = ""):
        with self._lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO feeds (url, title, pinned, added_at) VALUES (?,?,0,?)",
                (url, title, datetime.now().isoformat()))
            self.conn.commit()
        LOG.info(f"فید اضافه شد: {url}")

    def remove_feed(self, url: str):
        with self._lock:
            self.conn.execute("DELETE FROM feeds WHERE url=?", (url,))
            self.conn.execute("DELETE FROM items WHERE feed=?", (url,))
            self.conn.commit()
        LOG.info(f"فید حذف شد: {url}")

    def pin_feed(self, url: str, pinned: bool):
        with self._lock:
            self.conn.execute("UPDATE feeds SET pinned=? WHERE url=?", (int(pinned), url))
            self.conn.commit()

    def get_feeds(self) -> list:
        with self._lock:
            cur = self.conn.execute(
                "SELECT url, title, pinned FROM feeds ORDER BY pinned DESC, added_at ASC")
            return [{"url": r[0], "title": r[1], "pinned": bool(r[2])} for r in cur.fetchall()]

# ---------------------------------------------------------------------------
# بخش ۵: تصویر
# ---------------------------------------------------------------------------

def extract_image_from_feed_entry(entry) -> str | None:
    media = getattr(entry, "media_thumbnail", None)
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    media_content = getattr(entry, "media_content", None)
    if media_content and isinstance(media_content, list):
        for m in media_content:
            if m.get("medium") == "image" and m.get("url"):
                return m["url"]
            if m.get("url", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                return m["url"]
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")
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
    try:
        r = httpx.get(page_url, timeout=timeout,
                       headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        if r.status_code != 200:
            return None
        head = r.text[:8000]
        for pat in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        ]:
            m = re.search(pat, head, re.I)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def fetch_image_bytes(url: str, timeout: int = 10) -> bytes | None:
    try:
        r = httpx.get(url, timeout=timeout,
                       headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            return r.content
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# بخش ۶: فچ فید
# ---------------------------------------------------------------------------

def fetch_feed(feed_url: str, timeout: int = 20) -> list:
    LOG.info(f"دریافت فید: {feed_url}")
    try:
        r = httpx.get(feed_url, timeout=timeout,
                       headers={"User-Agent": "Mozilla/5.0 (compatible; RSSReader/1.0)"},
                       follow_redirects=True)
        if r.status_code != 200:
            LOG.warning(f"فید {feed_url} → {r.status_code}")
            return []
        feed = feedparser.parse(r.content)
        items = []
        for e in feed.entries:
            image_url = extract_image_from_feed_entry(e)
            items.append({
                "id":        e.get("id") or e.get("link") or e.get("title", ""),
                "title":     html.unescape(e.get("title", "(بدون عنوان)")),
                "link":      e.get("link", ""),
                "summary":   html.unescape(re.sub(r"<[^>]+>", "", e.get("summary", "")))[:600],
                "published": e.get("published", e.get("updated", "")),
                "image_url": image_url or "",
            })
        LOG.info(f"  → {len(items)} خبر از {feed_url}")
        return items
    except Exception as exc:
        LOG.error(f"خطا در فچ {feed_url}: {exc}")
        return []
