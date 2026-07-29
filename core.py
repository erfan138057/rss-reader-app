"""
core.py - RSS Reader engine
DNS scanner + DoH + feed fetch + images + video detection + SQLite + internet monitor + log
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
# Logger
# ---------------------------------------------------------------------------
class AppLogger:
    def __init__(self, max_lines=500):
        self._lines = []
        self._max = max_lines
        self._lock = threading.Lock()
        self._callbacks = []
        self.logger = logging.getLogger("RSSReader")
        self.logger.setLevel(logging.DEBUG)
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        self.logger.addHandler(h)

    def _write(self, level, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {level}  {msg}"
        with self._lock:
            self._lines.append(line)
            if len(self._lines) > self._max:
                self._lines = self._lines[-self._max:]
        for cb in list(self._callbacks):
            try: cb(line)
            except: pass

    def add_callback(self, cb):    self._callbacks.append(cb)
    def remove_callback(self, cb): self._callbacks = [c for c in self._callbacks if c is not cb]
    def get_lines(self):
        with self._lock: return list(self._lines)
    def info(self, m):    self.logger.info(m);    self._write("INFO ", m)
    def warning(self, m): self.logger.warning(m); self._write("WARN ", m)
    def error(self, m):   self.logger.error(m);   self._write("ERROR", m)
    def debug(self, m):   self.logger.debug(m);   self._write("DEBUG", m)

LOG = AppLogger()

# ---------------------------------------------------------------------------
# DoH resolver
# ---------------------------------------------------------------------------
def _is_ip(h):
    try: socket.inet_aton(h); return True
    except: return False

def doh_resolve(host, doh_ip, doh_host, timeout=3, verify=True):
    """Resolve host using DNS-over-HTTPS with proper error handling."""
    if _is_ip(host):
        return host
    
    try:
        url = f"https://{doh_ip}/dns-query"
        r = httpx.get(url, params={"name": host, "type": "A"},
                       headers={"Accept": "application/dns-json", "Host": doh_host},
                       timeout=timeout, verify=verify)
        
        if r.status_code == 200:
            for ans in r.json().get("Answer", []):
                if ans.get("type") == 1:
                    return ans["data"]
        
        # Fallback to non-verified request if first attempt failed
        if verify:
            return doh_resolve(host, doh_ip, doh_host, timeout, verify=False)
            
    except Exception as e:
        LOG.debug(f"DoH resolution failed for {host}@{doh_ip}: {e}")
        if verify:
            return doh_resolve(host, doh_ip, doh_host, timeout, verify=False)
    
    return None

_doh_lock = threading.Lock()

def install_doh_resolver(doh_ip, doh_host):
    with _doh_lock:
        orig = socket.getaddrinfo
        def patched(host, *a, **kw):
            if _is_ip(host): return orig(host, *a, **kw)
            ip = doh_resolve(host, doh_ip, doh_host)
            return orig(ip if ip else host, *a, **kw)
        socket.getaddrinfo = patched
    LOG.info(f"DoH active: {doh_host} ({doh_ip})")

# ---------------------------------------------------------------------------
# DNS Scanner (DoH)
# ---------------------------------------------------------------------------
_BLOCKED_IPS = {"10.10.34.34","10.10.34.35","10.10.34.36",
                 "178.22.122.100","185.55.226.26","185.55.225.25"}

def _is_blocked_ip(ip): return ip in _BLOCKED_IPS

class DNSScanner:
    TEST_DOMAIN = "www.google.com"

    def scan_server(self, server, filter_sites):
        result = {**server, "working": False, "latency_ms": None, "filters": {}}
        t0 = time.monotonic()
        ip = doh_resolve(self.TEST_DOMAIN, server["ip"], server["host"], timeout=4)
        if ip is None:
            LOG.warning(f"DNS {server['name']} no response")
            return result
        result["working"] = True
        result["latency_ms"] = round((time.monotonic() - t0) * 1000)
        LOG.info(f"DNS {server['name']} → {result['latency_ms']}ms")
        for site in filter_sites:
            try:
                res = doh_resolve(site, server["ip"], server["host"], timeout=3)
                result["filters"][site] = _is_blocked_ip(res) if res else None
            except: result["filters"][site] = None
        return result

    def scan_all(self, servers, filter_sites, progress_cb=None):
        results = [None] * len(servers)
        threads = []
        def worker(i, srv):
            r = self.scan_server(srv, filter_sites)
            results[i] = r
            if progress_cb: progress_cb(r)
        for i, srv in enumerate(servers):
            t = threading.Thread(target=worker, args=(i, srv), daemon=True)
            threads.append(t); t.start()
        for t in threads: t.join()
        return [r for r in results if r]

    def best_server(self, results):
        working = [r for r in results if r["working"]]
        if not working: return None
        return min(working, key=lambda r: (
            -sum(1 for v in r["filters"].values() if v is False),
            r["latency_ms"] or 9999))

# ---------------------------------------------------------------------------
# Plain DNS Scanner (port 53) — for when internet is cut
# ---------------------------------------------------------------------------
class PlainDNSScanner:
    TEST_DOMAIN = "google.com"

    def scan_ip(self, ip: str, timeout=3) -> dict:
        result = {"ip": ip, "working": False, "latency_ms": None}
        try:
            t0 = time.monotonic()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            # minimal DNS query for google.com A record
            query = (b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                     b"\x06google\x03com\x00\x00\x01\x00\x01")
            sock.sendto(query, (ip, 53))
            data, _ = sock.recvfrom(512)
            sock.close()
            if len(data) > 12:
                result["working"] = True
                result["latency_ms"] = round((time.monotonic() - t0) * 1000)
        except Exception:
            pass
        return result

    def scan_list(self, ips: list, progress_cb=None, max_workers=100) -> list:
        results = []
        lock = threading.Lock()
        sem = threading.Semaphore(max_workers)

        def worker(ip):
            with sem:
                r = self.scan_ip(ip)
                with lock:
                    results.append(r)
                if progress_cb: progress_cb(r)

        threads = [threading.Thread(target=worker, args=(ip,), daemon=True) for ip in ips]
        for t in threads: t.start()
        for t in threads: t.join()
        return sorted(results, key=lambda r: r["latency_ms"] or 9999)

# ---------------------------------------------------------------------------
# Internet Monitor
# ---------------------------------------------------------------------------
class InternetMonitor:
    PING_HOSTS = [("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443)]

    def __init__(self, interval=60, on_update=None):
        self.interval = interval
        self.on_update = on_update
        self._running = False
        self._last = {"percent": None, "label": "Checking...", "color": "gray"}

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self): self._running = False

    def _loop(self):
        while self._running:
            r = self._check()
            self._last = r
            if self.on_update: self.on_update(r)
            time.sleep(self.interval)

    def _check(self):
        ok, latencies = 0, []
        for host, port in self.PING_HOSTS:
            try:
                t0 = time.monotonic()
                s = socket.create_connection((host, port), timeout=4)
                s.close()
                latencies.append((time.monotonic() - t0) * 1000)
                ok += 1
            except: pass
        pct = round((ok / len(self.PING_HOSTS)) * 100)
        ms  = round(sum(latencies)/len(latencies)) if latencies else None
        if pct >= 80:
            label, color = f"Good ({ms}ms)" if ms else "Good", "#43A047"
        elif pct >= 40:
            label, color = f"Fair ({pct}%)", "#FB8C00"
        else:
            label, color = f"Poor ({pct}%)", "#E53935"
        LOG.info(f"Internet status: {pct}% — {label}")
        return {"percent": pct, "label": label, "color": color, "latency_ms": ms}

    @property
    def last(self): return self._last

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class Store:
    def __init__(self, db_file="rss_reader.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self._lock = threading.Lock()
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                id          TEXT PRIMARY KEY,
                feed        TEXT,
                title       TEXT,
                link        TEXT,
                published   TEXT,
                summary     TEXT,
                image_url   TEXT,
                video_url   TEXT,
                video_type  TEXT,
                seen        INTEGER DEFAULT 0,
                click_count INTEGER DEFAULT 0,
                bookmarked  INTEGER DEFAULT 0,
                bookmarked_at TEXT
            );
            CREATE TABLE IF NOT EXISTS feeds (
                url      TEXT PRIMARY KEY,
                title    TEXT,
                pinned   INTEGER DEFAULT 0,
                added_at TEXT
            );
        """)
        # migrate existing DB — add columns if missing
        for col, definition in [
            ("bookmarked",    "INTEGER DEFAULT 0"),
            ("bookmarked_at", "TEXT"),
        ]:
            try:
                self.conn.execute(f"ALTER TABLE items ADD COLUMN {col} {definition}")
                self.conn.commit()
            except Exception:
                pass
        LOG.info(f"DB opened: {db_file}")

    def upsert(self, item: dict, feed_url: str):
        with self._lock:
            self.conn.execute("""
                INSERT INTO items
                    (id,feed,title,link,published,summary,image_url,video_url,video_type,seen,click_count,bookmarked)
                VALUES (:id,:feed,:title,:link,:published,:summary,:image_url,:video_url,:video_type,0,0,0)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title, summary=excluded.summary,
                    image_url=COALESCE(excluded.image_url, items.image_url),
                    video_url=COALESCE(excluded.video_url, items.video_url),
                    video_type=COALESCE(excluded.video_type, items.video_type)
            """, {**item, "feed": feed_url})
            self.conn.commit()

    def mark_seen(self, item_id):
        with self._lock:
            self.conn.execute(
                "UPDATE items SET seen=1, click_count=click_count+1 WHERE id=?", (item_id,))
            self.conn.commit()

    def toggle_bookmark(self, item_id: str) -> bool:
        """Toggle bookmark. Returns new state (True = bookmarked)."""
        with self._lock:
            cur = self.conn.execute("SELECT bookmarked FROM items WHERE id=?", (item_id,))
            row = cur.fetchone()
            if row is None:
                return False
            new_state = 0 if row[0] else 1
            ts = datetime.now().isoformat() if new_state else None
            self.conn.execute(
                "UPDATE items SET bookmarked=?, bookmarked_at=? WHERE id=?",
                (new_state, ts, item_id))
            self.conn.commit()
            LOG.info(f"Bookmark {'added' if new_state else 'removed'}: {item_id[:40]}")
            return bool(new_state)

    def get_bookmarks(self, sort="newest") -> list:
        order = "bookmarked_at ASC" if sort == "oldest" else "bookmarked_at DESC"
        with self._lock:
            cur = self.conn.execute(
                f"SELECT * FROM items WHERE bookmarked=1 ORDER BY {order}")
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get_items(self, feed_url=None, sort="newest") -> list:
        order = "published ASC, rowid ASC" if sort == "oldest" else "published DESC, rowid DESC"
        with self._lock:
            q = f"SELECT * FROM items{' WHERE feed=?' if feed_url else ''} ORDER BY {order}"
            cur = self.conn.execute(q, (feed_url,) if feed_url else ())
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def update_image(self, item_id, image_url):
        with self._lock:
            self.conn.execute(
                "UPDATE items SET image_url=? WHERE id=? AND (image_url IS NULL OR image_url='')",
                (image_url, item_id))
            self.conn.commit()

    def add_feed(self, url, title=""):
        with self._lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO feeds (url,title,pinned,added_at) VALUES (?,?,0,?)",
                (url, title, datetime.now().isoformat()))
            self.conn.commit()
        LOG.info(f"Feed added: {url}")

    def remove_feed(self, url):
        with self._lock:
            self.conn.execute("DELETE FROM feeds WHERE url=?", (url,))
            self.conn.execute("DELETE FROM items WHERE feed=?", (url,))
            self.conn.commit()
        LOG.info(f"Feed removed: {url}")

    def pin_feed(self, url, pinned):
        with self._lock:
            self.conn.execute("UPDATE feeds SET pinned=? WHERE url=?", (int(pinned), url))
            self.conn.commit()

    def get_feeds(self) -> list:
        with self._lock:
            cur = self.conn.execute(
                "SELECT url,title,pinned FROM feeds ORDER BY pinned DESC, added_at ASC")
            return [{"url": r[0], "title": r[1], "pinned": bool(r[2])} for r in cur.fetchall()]

# ---------------------------------------------------------------------------
# Video detection helpers
# ---------------------------------------------------------------------------
def _detect_video_from_enclosures(entry):
    """Check video enclosures."""
    for enc in getattr(entry, "enclosures", []):
        url = enc.get("href") or enc.get("url", "")
        if enc.get("type","").startswith("video/") or VIDEO_EXT.search(url):
            return url, "direct"
    return "", ""

def _detect_video_from_media_content(entry):
    """Check media:content entries."""
    for m in getattr(entry, "media_content", []):
        url = m.get("url","")
        if m.get("medium") == "video" or VIDEO_EXT.search(url):
            return url, "direct"
    return "", ""

def _detect_video_from_link(link):
    """Check direct link patterns."""
    yt = YOUTUBE_RE.search(link)
    if yt: return f"https://www.youtube.com/watch?v={yt.group(1)}", "youtube"
    vm = VIMEO_RE.search(link)
    if vm: return f"https://vimeo.com/{vm.group(1)}", "vimeo"
    rg = REDGIFS_RE.search(link)
    if rg: return f"https://redgifs.com/watch/{rg.group(1)}", "redgifs"
    if VIDEO_EXT.search(link): return link, "direct"
    return "", ""

def _detect_video_from_text(text):
    """Check text content for video URLs."""
    for pat, vtype in [(YOUTUBE_RE,"youtube"),(VIMEO_RE,"vimeo"),(REDGIFS_RE,"redgifs")]:
        m = pat.search(text)
        if m:
            base = "https://www.youtube.com/watch?v=" if vtype=="youtube" else "https://vimeo.com/"
            id_  = m.group(1)
            return f"{base}{id_}", vtype
    ext = VIDEO_EXT.search(text)
    if ext:
        url_m = re.search(r'https?://\S+' + ext.group(1), text, re.I)
        if url_m: return url_m.group(0), "direct"
    return "", ""

# ---------------------------------------------------------------------------
# Video detection
# ---------------------------------------------------------------------------
YOUTUBE_RE = re.compile(
    r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})')
VIMEO_RE   = re.compile(r'(?:https?://)?(?:www\.)?vimeo\.com/(\d+)')
REDGIFS_RE = re.compile(r'(?:https?://)?(?:www\.)?redgifs\.com/watch/([A-Za-z0-9]+)')
VIDEO_EXT  = re.compile(r'\.(mp4|webm|mkv|avi|mov|m3u8)(\?|$)', re.I)

def detect_video(entry) -> tuple:
    """Returns (video_url, video_type) or ('', '')."""
    # Check in order of priority
    url, vtype = _detect_video_from_enclosures(entry)
    if url: return url, vtype
    
    url, vtype = _detect_video_from_media_content(entry)
    if url: return url, vtype
    
    link = getattr(entry, "link", "") or ""
    url, vtype = _detect_video_from_link(link)
    if url: return url, vtype
    
    # Check text content
    for field in ["summary", "content"]:
        val = getattr(entry, field, None)
        text = " ".join(v.get("value","") for v in val) if isinstance(val, list) else (val or "")
        url, vtype = _detect_video_from_text(text)
        if url: return url, vtype
    
    return "", ""

# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def extract_image_from_feed_entry(entry) -> str:
    media = getattr(entry, "media_thumbnail", None)
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    for m in getattr(entry, "media_content", []):
        if m.get("medium") == "image" and m.get("url"): return m["url"]
        if m.get("url","").lower().endswith((".jpg",".jpeg",".png",".webp",".gif")): return m["url"]
    for enc in getattr(entry, "enclosures", []):
        if enc.get("type","").startswith("image/"): return enc.get("href") or enc.get("url","")
    for field in ["summary","content"]:
        val = getattr(entry, field, None)
        text = " ".join(v.get("value","") for v in val) if isinstance(val,list) else (val or "")
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', text, re.I)
        if m and m.group(1).startswith("http"): return m.group(1)
    return ""

def fetch_og_image(page_url, timeout=8) -> str:
    try:
        r = httpx.get(page_url, timeout=timeout,
                       headers={"User-Agent":"Mozilla/5.0"}, follow_redirects=True)
        head = r.text[:8000]
        for pat in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        ]:
            m = re.search(pat, head, re.I)
            if m: return m.group(1)
    except Exception as e:
        LOG.debug(f"OG image fetch failed {page_url}: {e}")
    return ""

def fetch_image_bytes(url, timeout=10) -> bytes:
    try:
        r = httpx.get(url, timeout=timeout,
                       headers={"User-Agent":"Mozilla/5.0"}, follow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type",""):
            return r.content
    except Exception as e:
        LOG.debug(f"Image fetch failed {url}: {e}")
    return b""

# ---------------------------------------------------------------------------
# Caching for better performance
# ---------------------------------------------------------------------------
_feed_cache = {}
_CACHE_TIMEOUT = 300  # 5 minutes

# ---------------------------------------------------------------------------
# Feed fetch with caching
# ---------------------------------------------------------------------------
def fetch_feed(feed_url, timeout=20) -> list:
    """Fetch RSS feed with caching support."""
    # Check cache first
    cache_key = f"{feed_url}_{timeout}"
    if cache_key in _feed_cache:
        cached_data, timestamp = _feed_cache[cache_key]
        if time.time() - timestamp < _CACHE_TIMEOUT:
            LOG.debug(f"Cache hit for {feed_url}")
            return cached_data
    
    LOG.info(f"Fetching: {feed_url}")
    try:
        r = httpx.get(feed_url, timeout=timeout,
                       headers={"User-Agent":"Mozilla/5.0 (compatible; RSSReader/1.0)"},
                       follow_redirects=True)
        if r.status_code != 200:
            LOG.warning(f"Feed {feed_url} → {r.status_code}")
            return []
        
        feed = feedparser.parse(r.content)
        items = []
        for e in feed.entries:
            video_url, video_type = detect_video(e)
            items.append({
                "id":         e.get("id") or e.get("link") or e.get("title",""),
                "title":      html.unescape(e.get("title","(no title)")),
                "link":       e.get("link",""),
                "summary":    html.unescape(re.sub(r"<[^>]+>","", e.get("summary","")))[:800],
                "published":  e.get("published", e.get("updated","")),
                "image_url":  extract_image_from_feed_entry(e),
                "video_url":  video_url,
                "video_type": video_type,
            })
        
        # Cache the results
        _feed_cache[cache_key] = (items, time.time())
        
        LOG.info(f"  → {len(items)} articles from {feed_url}")
        return items
    except Exception as exc:
        LOG.error(f"Fetch error {feed_url}: {exc}")
        return []

def clear_cache():
    """Clear the feed cache."""
    _feed_cache.clear()
    LOG.info("Feed cache cleared")

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
def check_dependencies():
    """Check if required dependencies are available."""
    missing = []
    
    # Check VLC
    try:
        import vlc
    except ImportError:
        missing.append("python-vlc (for video playback)")
    
    # Check PIL/Pillow
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow (for image display)")
    
    # Check httpx
    try:
        import httpx
    except ImportError:
        missing.append("httpx (for HTTP requests)")
    
    # Check feedparser
    try:
        import feedparser
    except ImportError:
        missing.append("feedparser (for RSS parsing)")
    
    if missing:
        LOG.warning(f"Missing dependencies: {', '.join(missing)}")
        LOG.warning("Some features may not work properly")
        return False
    
    LOG.info("All dependencies available")
    return True
