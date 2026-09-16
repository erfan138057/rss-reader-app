"""
config.py - App configuration
"""
import os
import sys
import json
import shutil

_APP_BASE = os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    """Return a durable per-user data directory for frozen desktop builds."""
    if not getattr(sys, "frozen", False):
        return _APP_BASE
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        root = os.path.expanduser("~/Library/Application Support")
    else:
        root = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    path = os.path.join(root, "RSSReaderPro")
    os.makedirs(path, exist_ok=True)
    return path


_DATA_DIR = _data_dir()
DB_FILE       = os.path.join(_DATA_DIR, "rss_reader.db")
SETTINGS_FILE = os.path.join(_DATA_DIR, "settings.json")

# One-file builds extract into a temporary directory. Copy legacy side-by-side
# data once when present, rather than creating an empty profile on upgrade.
if getattr(sys, "frozen", False):
    _legacy_dir = os.path.dirname(sys.executable)
    for _name in ("rss_reader.db", "settings.json"):
        _target = os.path.join(_DATA_DIR, _name)
        _legacy = os.path.join(_legacy_dir, _name)
        if not os.path.exists(_target) and os.path.exists(_legacy):
            try:
                shutil.copy2(_legacy, _target)
            except OSError:
                pass

DOH_SERVERS = [
    {"name": "Cloudflare",     "ip": "1.1.1.1",         "host": "cloudflare-dns.com"},
    {"name": "Cloudflare Alt", "ip": "1.0.0.1",         "host": "cloudflare-dns.com"},
    {"name": "Google",         "ip": "8.8.8.8",         "host": "dns.google"},
    {"name": "Google Alt",     "ip": "8.8.4.4",         "host": "dns.google"},
    {"name": "Quad9",          "ip": "9.9.9.9",         "host": "dns.quad9.net"},
    {"name": "Quad9 Alt",      "ip": "149.112.112.112", "host": "dns.quad9.net"},
    {"name": "AdGuard",        "ip": "94.140.14.14",    "host": "dns.adguard.com"},
    {"name": "AdGuard Alt",    "ip": "94.140.15.15",    "host": "dns.adguard.com"},
    {"name": "NextDNS",        "ip": "45.90.28.0",      "host": "dns.nextdns.io"},
    {"name": "OpenDNS",        "ip": "208.67.222.222",  "host": "doh.opendns.com"},
]

# Compatible IP: no hard-coded override. System DNS is used by default;
# DoH is only activated when user enables it (settings dns_auto or scanner).
# This keeps the app working with the origin country's IP without VPN.
ACTIVE_DOH     = None  # was DOH_SERVERS[0] — now opt-in
CHECK_INTERVAL = 300

DEFAULT_FEEDS = [
    # منابع فارسی عمومی و دسته‌بندی‌شده
    ("https://feeds.bbci.co.uk/persian/rss.xml", "بی‌بی‌سی فارسی", "اخبار"),
    ("https://www.irna.ir/rss", "ایرنا", "اخبار"),
    ("https://www.isna.ir/rss", "ایسنا", "اخبار"),
    ("https://www.mehrnews.com/rss", "مهر", "اخبار"),
    ("https://www.tabnak.ir/fa/rss/allnews", "تابناک", "اخبار"),
    # منابع بین‌المللی برای پوشش گسترده‌تر
    ("https://feeds.bbci.co.uk/news/rss.xml", "BBC News", "World"),
    ("https://www.theguardian.com/world/rss", "The Guardian", "World"),
]

FILTER_TEST_SITES = [
    "www.google.com", "www.youtube.com", "twitter.com",
    "www.instagram.com", "t.me", "www.reddit.com",
    "www.bbc.com", "www.theguardian.com",
]

# Default settings
DEFAULTS = {
    "theme":          "dark",
    "language":       "en",
    "check_interval": 300,
    "sort":           "newest",
    "show_read":      True,
    "load_images":    True,
    "font_size":      9,
    "card_style":     "telegram",
    # Direct video uses the native Qt player inside the application by default.
    # Unsupported providers remain delegated to the user's system player.
    "video_playback_mode": "in_app",
    "video_internal": False,  # legacy Tkinter default remains system-player based
    "external_player_path": "",  # optional user-selected system player path
    "dns_auto":       False,
    "notifications":  True,
    "auto_scroll":    False,
    "auto_scroll_speed": 2,
    "deleted_feeds":  [],   # feeds the user explicitly removed — never re-add
    "added_feeds":    [],   # feeds the user manually added — always re-add
    # Pro licensing — key filled by buyer, secret read from env at runtime
    "pro_key":        "",    # empty = Free edition
    "pro_worker_url": "",    # Cloudflare Worker address, user-provided, never hardcoded
}

def load_settings() -> dict:
    s = dict(DEFAULTS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                s.update(json.load(f))
        except Exception:
            pass
    return s

def save_settings(data: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
