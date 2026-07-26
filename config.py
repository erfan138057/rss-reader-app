"""
config.py - App configuration
"""
import os
import json

_BASE = os.path.dirname(os.path.abspath(__file__))
DB_FILE       = os.path.join(_BASE, "rss_reader.db")
SETTINGS_FILE = os.path.join(_BASE, "settings.json")

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

ACTIVE_DOH     = DOH_SERVERS[0]
CHECK_INTERVAL = 300

DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/persian/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://rss.cnn.com/rss/edition.rss",
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
    "video_internal": True,
    "dns_auto":       False,
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
