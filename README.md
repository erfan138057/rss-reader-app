<meta name="google-site-verification" content="jUdMhILMMS6nFdTtg00tQIXkAzidBCkM-dcPaSA-ZRo" />

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.3-blue?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/python-3.8+-green?style=for-the-badge" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/github/stars/erfan138057/rss-reader-app?style=for-the-badge" alt="Stars">
  <img src="https://img.shields.io/github/downloads/erfan138057/rss-reader-app/total?style=for-the-badge" alt="Downloads">
</p>

---

<!-- ENGLISH VERSION -->

# 📡 RSS Reader Pro

**Professional RSS Desktop App with DNS-over-HTTPS censorship bypass**

> **v1.0.3 is here:** a faster reading workflow with advanced search, categories, Reader Mode, OPML transfer, bookmark exports, notifications and auto-scroll.

<p align="center">
  <a href="https://github.com/erfan138057/rss-reader-app/releases/latest">
    <img src="https://img.shields.io/badge/📥_Download_Latest-0078D4?style=for-the-badge&logo=windows" alt="Download">
  </a>
<a href="https://github.com/erfan138057/rss-reader-app/discussions">
    <img src="https://img.shields.io/badge/💬_Discussions-2CA5E0?style=for-the-badge&logo=github" alt="Discussions">
  </a>
  <a href="https://github.com/erfan138057/rss-reader-app/issues">
    <img src="https://img.shields.io/badge/🐛_Issues-red?style=for-the-badge&logo=github" alt="Issues">
  </a>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔐 DNS-over-HTTPS | Bypass internet filters with DoH |
| 🔖 Bookmarks | Save articles with one click |
| 🎬 Video Playback | Opens with each user's system-default player; optional internal VLC mode for compatible direct videos |
| 🎨 Dual UI | Reddit-style & Telegram-style views |
| 🌙 Dark / Light | Switchable themes |
| ⚡ Smart Cache | Fast performance with local caching |
| 🛡️ Privacy First | 100% local — no data sent anywhere |
| 🔍 Auto Detection | Automatic video & image extraction |
| 🗂️ Feed Manager | Add, remove, pin feeds |
| 📋 App Log | Built-in log viewer for debugging |
| ⌨️ Keyboard shortcuts | `Space` scrolls, `B` bookmarks and `O` opens the active article |
| 🔎 Advanced search | Filter by text, date, unread state and bookmarks |
| 🗂️ Feed categories | Group feeds such as News, Tech and Sports; see unread counts per feed |
| 📖 Reader Mode | Clean, distraction-free article text from the source page |
| ⇄ OPML & exports | Import/export feeds via OPML and export bookmarks as HTML or PDF |
| 🔔 Reading controls | Optional new-item notifications, font-size slider and auto-scroll |

---

## 🚀 Quick Start

### Download (Windows — No Install Needed)

[![Download EXE](https://img.shields.io/badge/📥_Download_Windows_EXE-0078D4?style=for-the-badge&logo=windows)](https://github.com/erfan138057/rss-reader-app/releases/latest)

The Windows executable is built with the official RSS Reader Pro icon. The release workflow can additionally apply Microsoft Artifact Signing after the project owner configures its Azure identity. See [the SmartScreen signing guide](docs/SMARTSCREEN.md) for the required one-time setup and the limits of reputation-based warnings.

### Download (Linux x86_64 — Portable)

Download `RSS-Reader-Pro-v*-linux-x86_64.tar.gz` from [Releases](https://github.com/erfan138057/rss-reader-app/releases/latest), then extract and launch it:

```bash
tar -xzf RSS-Reader-Pro-v*-linux-x86_64.tar.gz
cd RSS-Reader-Pro-v*-linux-x86_64
./RSS-Reader-Pro
```

### Run from Source

```bash
git clone https://github.com/erfan138057/rss-reader-app.git
cd rss-reader-app
pip install -r requirements.txt
python gui.py
```

**Requirements:** Python 3.8+ · VLC Media Player (optional, for video)

---

## 🎯 Perfect For

- 🇮🇷 **Iranian users** — bypass DNS filtering out of the box
- 🔒 **Privacy enthusiasts** — fully offline, zero telemetry
- 📰 **News readers** — modern Signal Modular dashboard with visual story cards and a focused reading workspace
- 🎬 **Video consumers** — YouTube playback built in
- 🐍 **Python developers** — clean modular codebase

---

## 🛠️ Built With

- **Python 3.8+** — core language
- **PySide6 / Qt** — modern desktop GUI framework with custom cards, responsive layouts and a native Windows rendering pipeline
- **SQLite** — local data storage
- **httpx** — HTTP client with DoH support
- **feedparser** — RSS/Atom parsing
- **Pillow** — image processing
- **System default media handler** — opens videos with the player chosen by each user; VLC is optional for internal playback only

---

## 🤝 Contributing

- 🐛 **Report bugs** — open an Issue
- 💡 **Suggest features** — post in Discussions
- 🔧 **Submit code** — send a Pull Request
- 📖 **Improve docs** — every contribution helps

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

### ⭐ Star this project if you find it useful! ⭐

</div>

---

<!-- PERSIAN VERSION -->

<p align="center">
  <img src="https://img.shields.io/badge/🇮🇷_نسخه_فارسی-006A4E?style=for-the-badge" alt="Persian">
</p>

<div dir="rtl" align="right">

# 📡 آر‌اس‌اس‌خوان حرفه‌ای

**اپلیکیشن دسکتاپ مدیریت فید RSS با دور زدن فیلترینگ**

> **نسخهٔ ۱.۰.۳ منتشر شد:** تجربهٔ خواندن سریع‌تر با جست‌وجوی پیشرفته، دسته‌بندی، حالت مطالعه، انتقال OPML، خروجی نشان‌گذاری‌ها، اعلان و پیمایش خودکار.

<p align="center">
  <a href="https://github.com/erfan138057/rss-reader-app/releases/latest">
    <img src="https://img.shields.io/badge/📥_دانلود_آخرین_نسخه-0078D4?style=for-the-badge&logo=windows" alt="دانلود">
  </a>
<a href="https://github.com/erfan138057/rss-reader-app/discussions">
    <img src="https://img.shields.io/badge/💬_گفتگو-2CA5E0?style=for-the-badge&logo=github" alt="گفتگو">
  </a>
  <a href="https://github.com/erfan138057/rss-reader-app/issues">
    <img src="https://img.shields.io/badge/🐛_گزارش_باگ-red?style=for-the-badge&logo=github" alt="باگ">
  </a>
</p>

---

## ✨ ویژگی‌ها

| ویژگی | توضیح |
|-------|-------|
| 🔐 DNS-over-HTTPS | دور زدن فیلترینگ اینترنت |
| 🔖 نشان‌گذاری | ذخیره مقالات با یک کلیک |
| 🎬 پخش ویدیو | بازشدن با پلیر پیش‌فرض هر کاربر؛ VLC فقط برای پخش داخلی اختیاری است |
| 🎨 دو رابط | نمای ردیت و تلگرام |
| 🌙 دارک/لایت | تم تیره و روشن |
| ⚡ کش هوشمند | سرعت بالا با ذخیره محلی |
| 🛡️ حریم خصوصی | ۱۰۰٪ محلی، بدون ارسال داده |
| 🔍 تشخیص خودکار | استخراج خودکار ویدیو و تصویر |
| 🗂️ مدیریت فید | افزودن، حذف، پین کردن فیدها |
| 📋 لاگ برنامه | مشاهده لاگ و خطاها |
| ⌨️ میانبرهای صفحه‌کلید | `Space` برای پیمایش، `B` برای نشان‌گذاری و `O` برای بازکردن خبر فعال |
| 🔎 جست‌وجوی پیشرفته | فیلتر متن، بازهٔ تاریخ، فقط نخوانده و فقط نشان‌گذاری‌شده |
| 🗂️ دسته‌بندی فید | گروه‌بندی فیدها مانند اخبار، فناوری و ورزش؛ همراه با شمارندهٔ نخوانده |
| 📖 حالت مطالعه | نمایش متن تمیز و بدون اجزای مزاحم از صفحهٔ اصلی خبر |
| ⇄ OPML و خروجی | ورود/خروج فیدها با OPML و خروجی HTML یا PDF از نشان‌گذاری‌ها |
| 🔔 کنترل خواندن | اعلان خبرهای تازه، لغزندهٔ اندازهٔ فونت و پیمایش خودکار |

---

## 🚀 شروع سریع

### دانلود (ویندوز — بدون نصب)

[![دانلود EXE](https://img.shields.io/badge/📥_دانلود_ویندوز-0078D4?style=for-the-badge&logo=windows)](https://github.com/erfan138057/rss-reader-app/releases/latest)

فایل ویندوزی با آیکون رسمی RSS Reader Pro ساخته می‌شود. workflow انتشار برای امضای رسمی **Microsoft Artifact Signing** نیز آماده است؛ فعال‌سازی آن به تکمیل هویت Azure مالک پروژه نیاز دارد. راهنمای کامل و محدودیت‌های هشدار مبتنی بر شهرت در [راهنمای SmartScreen](docs/SMARTSCREEN.md) آمده است.

### دانلود (لینوکس x86_64 — قابل‌حمل)

فایل `RSS-Reader-Pro-v*-linux-x86_64.tar.gz` را از [Releases](https://github.com/erfan138057/rss-reader-app/releases/latest) دریافت کنید، سپس آن را استخراج و اجرا کنید:

```bash
tar -xzf RSS-Reader-Pro-v*-linux-x86_64.tar.gz
cd RSS-Reader-Pro-v*-linux-x86_64
./RSS-Reader-Pro
```

### اجرا از سورس

```bash
git clone https://github.com/erfan138057/rss-reader-app.git
cd rss-reader-app
pip install -r requirements.txt
python gui.py
```

**پیش‌نیازها:** Python 3.8+ · VLC (اختیاری، برای پخش ویدیو)

---

## 🤝 مشارکت

- 🐛 **گزارش باگ** — یک Issue باز کنید
- 💡 **پیشنهاد فیچر** — در Discussions بنویسید
- 🔧 **ارسال کد** — Pull Request بفرستید
- 📖 **بهبود مستندات** — هر کمکی ارزشمنده

---

## 📜 مجوز

مجوز MIT — برای جزئیات فایل [LICENSE](LICENSE) را ببینید.

---

<div align="center">

### ⭐ اگر این پروژه مفید بود، ستاره بدید! ⭐

</div>

</div>
