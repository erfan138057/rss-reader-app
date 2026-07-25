"""
config.py - تنظیمات برنامه
"""
import os

# سرورهای DoH برای اسکن و استفاده
DOH_SERVERS = [
    {"name": "Cloudflare",    "ip": "1.1.1.1",        "host": "cloudflare-dns.com"},
    {"name": "Cloudflare Alt","ip": "1.0.0.1",        "host": "cloudflare-dns.com"},
    {"name": "Google",        "ip": "8.8.8.8",        "host": "dns.google"},
    {"name": "Google Alt",    "ip": "8.8.4.4",        "host": "dns.google"},
    {"name": "Quad9",         "ip": "9.9.9.9",        "host": "dns.quad9.net"},
    {"name": "Quad9 Alt",     "ip": "149.112.112.112","host": "dns.quad9.net"},
    {"name": "AdGuard",       "ip": "94.140.14.14",   "host": "dns.adguard.com"},
    {"name": "AdGuard Alt",   "ip": "94.140.15.15",   "host": "dns.adguard.com"},
    {"name": "NextDNS",       "ip": "45.90.28.0",     "host": "dns.nextdns.io"},
    {"name": "OpenDNS",       "ip": "208.67.222.222", "host": "doh.opendns.com"},
]

# سرور فعال پیش‌فرض (ممکنه توسط اسکنر تغییر کنه)
ACTIVE_DOH = DOH_SERVERS[0]

# بازه بررسی خودکار (ثانیه). 0 یعنی غیرفعال
CHECK_INTERVAL = 300

# فیدهای پیش‌فرض
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/persian/rss.xml",
    "https://www.theguardian.com/world/rss",
    "https://rss.cnn.com/rss/edition.rss",
]

# سایت‌هایی که برای تست فیلتر بودن چک میشن
FILTER_TEST_SITES = [
    "www.google.com",
    "www.youtube.com",
    "twitter.com",
    "www.instagram.com",
    "t.me",
    "www.reddit.com",
    "www.bbc.com",
    "www.theguardian.com",
]

# مسیر دیتابیس
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rss_reader.db")
