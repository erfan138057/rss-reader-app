"""
gui.py - پنجره گرافیکی (Tkinter) برای RSS Reader
روی ویندوز با پایتون معمولی اجرا می‌شه (نیاز به نصب اضافه نداره).
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import webbrowser

import core
import config

# نصب رزولوشن DNS از طریق DoH (قبل از هر درخواست)
core.install_doh_resolver(config.DOH_IP, config.DOH_HOST)


class RSSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RSS خوان - با DoH (ضد فیلتر DNS)")
        self.root.geometry("820x560")

        self.store = core.Store(config.DB_FILE)
        self.feeds = list(config.DEFAULT_FEEDS)
        self.items = []  # لیست خبرهای نمایش داده شده

        self._build_ui()
        self._refresh_feeds_list()
        self._start_auto_check()

    # ---------------- ساخت رابط کاربری ----------------
    def _build_ui(self):
        # فریم بالا: مدیریت فیدها
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Label(top, text="فیدها:").pack(side="left")
        self.feed_var = tk.StringVar()
        self.feed_combo = ttk.Combobox(top, textvariable=self.feed_var, width=55, state="readonly")
        self.feed_combo.pack(side="left", padx=6)
        self.feed_combo.bind("<<ComboboxSelected>>", lambda e: self._load_feed())

        ttk.Button(top, text="➕ افزودن", command=self._add_feed).pack(side="left", padx=2)
        ttk.Button(top, text="🗑 حذف", command=self._del_feed).pack(side="left", padx=2)
        ttk.Button(top, text="🔄 چک همه", command=self._check_all).pack(side="left", padx=2)

        # فریم وسط: لیست خبرها
        mid = ttk.Frame(self.root)
        mid.pack(fill="both", expand=True, padx=8)

        self.listbox = tk.Listbox(mid, font=("Tahoma", 10), selectmode="single")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        scroll = ttk.Scrollbar(mid, orient="vertical", command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scroll.set)

        # فریم پایین: جزئیات خبر
        bot = ttk.Frame(self.root)
        bot.pack(fill="both", expand=True, padx=8, pady=6)

        self.detail = scrolledtext.ScrolledText(bot, font=("Tahoma", 10), wrap="word", height=10)
        self.detail.pack(fill="both", expand=True)

        self.open_btn = ttk.Button(bot, text="🔗 باز کردن لینک در مرورگر", command=self._open_link, state="disabled")
        self.open_btn.pack(anchor="e", pady=4)

        # نوار وضعیت
        self.status = ttk.Label(self.root, text="آماده", relief="sunken", anchor="e")
        self.status.pack(fill="x", side="bottom")

    # ---------------- منطق ----------------
    def _refresh_feeds_list(self):
        self.feed_combo["values"] = self.feeds
        if self.feeds:
            self.feed_combo.current(0)

    def _add_feed(self):
        url = tk.simpledialog.askstring("افزودن فید", "آدرس RSS را وارد کنید:")
        if url and url.strip():
            url = url.strip()
            if url not in self.feeds:
                self.feeds.append(url)
                self._refresh_feeds_list()
                self.feed_combo.set(url)
                self._load_feed()

    def _del_feed(self):
        cur = self.feed_var.get()
        if cur in self.feeds:
            self.feeds.remove(cur)
            self._refresh_feeds_list()
            self.listbox.delete(0, "end")
            self.detail.delete("1.0", "end")

    def _load_feed(self):
        url = self.feed_var.get()
        if not url:
            return
        self._set_status(f"در حال بارگیری: {url}")
        threading.Thread(target=self._worker, args=(url,), daemon=True).start()

    def _check_all(self):
        self._set_status("بررسی همه فیدها...")
        threading.Thread(target=self._check_all_worker, daemon=True).start()

    def _worker(self, url):
        items = core.fetch_feed(url)
        # فقط خبرهای جدید (ندیده‌شده) رو نگه می‌داریم
        new_items = []
        for it in items:
            if not self.store.is_seen(it["id"]):
                new_items.append(it)
        self.root.after(0, self._show_items, new_items, url)

    def _check_all_worker(self):
        all_new = []
        for url in self.feeds:
            items = core.fetch_feed(url)
            for it in items:
                if not self.store.is_seen(it["id"]):
                    all_new.append(it)
            time.sleep(1)
        self.root.after(0, self._show_items, all_new, "همه فیدها")

    def _show_items(self, items, source):
        self.items = items
        self.listbox.delete(0, "end")
        for it in items:
            self.listbox.insert("end", it["title"])
        if items:
            self._set_status(f"{len(items)} خبر جدید از {source}")
        else:
            self._set_status(f"خبر جدیدی نیست - {source}")
        self.detail.delete("1.0", "end")
        self.open_btn.config(state="disabled")

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        it = self.items[idx]
        self.detail.delete("1.0", "end")
        text = f"📰 {it['title']}\n\n{it['published']}\n\n{it['summary']}\n\n🔗 {it['link']}"
        self.detail.insert("1.0", text)
        self.open_btn.config(state="normal")
        # علامت به عنوان دیده‌شده (دیگه تکرار نشه)
        self.store.mark(it["id"], self.feed_var.get(), it["title"], it["link"], it["published"])

    def _open_link(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        it = self.items[sel[0]]
        if it["link"]:
            webbrowser.open(it["link"])

    def _set_status(self, msg):
        self.status.config(text=msg)

    def _start_auto_check(self):
        if config.CHECK_INTERVAL > 0:
            def loop():
                while True:
                    time.sleep(config.CHECK_INTERVAL)
                    self._check_all_worker()
            threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    import tkinter.simpledialog  # اطمینان از موجود بودن
    root = tk.Tk()
    try:
        # فونت فارسی بهتر روی ویندوز
        root.tk.call("font", "configure", "TkDefaultFont", "-family", "Tahoma")
    except Exception:
        pass
    app = RSSApp(root)
    root.mainloop()
