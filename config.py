"""
config.py - تنظیمات برنامه (قابل ویرایش توسط کاربر)
"""
import os

# آدرس سرور DoH (IP ثابت - به DNS سیستم وابسته نیست)
# گزینه‌های رایگان رایج:
#   Cloudflare: IP=1.1.1.1  host=cloudflare-dns.com
#   Google:      IP=8.8.8.8  host=dns.google
DOH_IP = "1.1.1.1"
DOH_HOST = "cloudflare-dns.com"

# بازه بررسی خودکار (ثانیه). 0 یعنی فقط با دکمه چک کن.
CHECK_INTERVAL = 300

# فیدهای پیش‌فرض (کاربر می‌تونه از داخل برنامه اضافه/حذف کنه)
DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/persian/rss.xml",
    "https://www.theguardian.com/world/rss",
]

# مسیر فایل دیتابیس
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rss_reader.db")
