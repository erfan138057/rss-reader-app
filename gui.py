"""
gui.py - رابط کاربری به سبک تلگرام
"""
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading
import time
import webbrowser
import io
import queue

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

import core
import config

# ---------------------------------------------------------------------------
# رنگ‌ها و استایل (تم تلگرام تیره)
# ---------------------------------------------------------------------------
COLORS = {
    "bg":           "#17212B",   # پس‌زمینه اصلی
    "sidebar":      "#0E1621",   # نوار کناری
    "card":         "#1E2C3A",   # کارت خبر
    "card_seen":    "#17212B",   # کارت خبر خوانده‌شده
    "card_hover":   "#243447",   # hover
    "accent":       "#2196F3",   # آبی تلگرام
    "accent2":      "#64B5F6",   # آبی روشن‌تر
    "text_primary": "#FFFFFF",
    "text_secondary":"#7B8EA0",
    "text_seen":    "#5B6C7D",   # متن خوانده‌شده
    "badge":        "#2196F3",   # نشانگر خوانده‌نشده
    "separator":    "#0E1621",
    "input_bg":     "#242F3D",
    "btn":          "#2196F3",
    "btn_hover":    "#1976D2",
    "danger":       "#E53935",
    "success":      "#43A047",
    "warning":      "#FB8C00",
    "panel":        "#1C2A38",
}

FONT_TITLE   = ("Tahoma", 10, "bold")
FONT_SUMMARY = ("Tahoma", 9)
FONT_META    = ("Tahoma", 8)
FONT_LARGE   = ("Tahoma", 12, "bold")
FONT_BTN     = ("Tahoma", 9)
FONT_MONO    = ("Courier New", 9)


# ---------------------------------------------------------------------------
# ابزارهای کمکی UI
# ---------------------------------------------------------------------------

def make_placeholder_image(w=80, h=60, color="#243447"):
    """تصویر placeholder وقتی تصویری نیست."""
    if not PIL_OK:
        return None
    img = Image.new("RGB", (w, h), color)
    draw = ImageDraw.Draw(img)
    # آیکون ساده
    draw.rectangle([w//4, h//4, 3*w//4, 3*h//4], outline="#3A5068", width=1)
    draw.line([w//4, h//4, 3*w//4, 3*h//4], fill="#3A5068", width=1)
    draw.line([3*w//4, h//4, w//4, 3*h//4], fill="#3A5068", width=1)
    return ImageTk.PhotoImage(img)


def resize_image(data: bytes, w: int, h: int):
    """تبدیل bytes به PhotoImage با اندازه مشخص."""
    if not PIL_OK or not data:
        return None
    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        img.thumbnail((w, h), Image.LANCZOS)
        # crop مرکزی
        iw, ih = img.size
        left = (iw - min(iw, w)) // 2
        top  = (ih - min(ih, h)) // 2
        img = img.crop((left, top, left + min(iw, w), top + min(ih, h)))
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ویجت کارت خبر
# ---------------------------------------------------------------------------

class NewsCard(tk.Frame):
    THUMB_W = 80
    THUMB_H = 60

    def __init__(self, master, item: dict, on_click, on_image_loaded, **kw):
        seen = bool(item.get("seen"))
        bg = COLORS["card_seen"] if seen else COLORS["card"]
        super().__init__(master, bg=bg, cursor="hand2", **kw)
        self.item = item
        self.on_click = on_click
        self.on_image_loaded = on_image_loaded
        self._bg = bg
        self._photo = None
        self._placeholder = make_placeholder_image(self.THUMB_W, self.THUMB_H)

        self._build()
        self._bind_hover()
        self._load_image_async()

    def _build(self):
        seen = bool(self.item.get("seen"))
        text_color = COLORS["text_seen"] if seen else COLORS["text_primary"]
        meta_color = COLORS["text_seen"] if seen else COLORS["text_secondary"]

        # تصویر
        self.img_label = tk.Label(
            self, bg=self._bg,
            image=self._placeholder,
            width=self.THUMB_W, height=self.THUMB_H,
        )
        self.img_label.image = self._placeholder
        self.img_label.pack(side="left", padx=(10, 8), pady=8)

        # متن
        text_frame = tk.Frame(self, bg=self._bg)
        text_frame.pack(side="left", fill="both", expand=True, pady=8, padx=(0, 8))

        title = self.item.get("title", "")
        lbl_title = tk.Label(
            text_frame, text=title,
            font=FONT_TITLE, fg=text_color, bg=self._bg,
            anchor="w", justify="left", wraplength=420,
        )
        lbl_title.pack(anchor="w")

        summary = self.item.get("summary", "")
        if summary:
            lbl_sum = tk.Label(
                text_frame, text=summary[:120] + ("…" if len(summary) > 120 else ""),
                font=FONT_SUMMARY, fg=meta_color, bg=self._bg,
                anchor="w", justify="left", wraplength=420,
            )
            lbl_sum.pack(anchor="w", pady=(2, 0))

        pub = self.item.get("published", "")
        feed = self.item.get("feed", "")
        domain = ""
        try:
            from urllib.parse import urlparse as up
            domain = up(feed).netloc
        except Exception:
            pass
        meta_text = f"{pub[:16]}  •  {domain}" if domain else pub[:16]
        lbl_meta = tk.Label(
            text_frame, text=meta_text,
            font=FONT_META, fg=meta_color, bg=self._bg,
            anchor="w",
        )
        lbl_meta.pack(anchor="w", pady=(3, 0))

        # نشانگر خوانده‌نشده
        if not seen:
            dot = tk.Label(self, text="●", fg=COLORS["badge"], bg=self._bg, font=("", 8))
            dot.pack(side="right", padx=8)

        # خط جداکننده
        sep = tk.Frame(self, height=1, bg=COLORS["separator"])
        sep.pack(side="bottom", fill="x")

        # bind همه child widgetها
        for w in self.winfo_children():
            self._bind_widget(w)
        # bind recursively for text_frame children
        for w in text_frame.winfo_children():
            self._bind_widget(w)

    def _bind_widget(self, w):
        w.bind("<Button-1>", self._clicked)
        w.bind("<Enter>", self._hover_on)
        w.bind("<Leave>", self._hover_off)

    def _bind_hover(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Enter>", self._hover_on)
        self.bind("<Leave>", self._hover_off)

    def _hover_on(self, e=None):
        self._set_bg(COLORS["card_hover"])

    def _hover_off(self, e=None):
        self._set_bg(self._bg)

    def _set_bg(self, color):
        self.configure(bg=color)
        for w in self.winfo_children():
            try:
                w.configure(bg=color)
            except Exception:
                pass

    def _clicked(self, e=None):
        self.on_click(self.item)

    def _load_image_async(self):
        def worker():
            url = self.item.get("image_url", "")
            data = None
            if url:
                data = core.fetch_image_bytes(url)
            if not data and self.item.get("link"):
                # سعی کن از صفحه خبر بگیری
                og = core.fetch_og_image(self.item["link"])
                if og:
                    self.item["image_url"] = og
                    data = core.fetch_image_bytes(og)
            if data:
                photo = resize_image(data, self.THUMB_W, self.THUMB_H)
                if photo:
                    self.after(0, self._set_image, photo, url or self.item.get("image_url",""))
        threading.Thread(target=worker, daemon=True).start()

    def _set_image(self, photo, url):
        self._photo = photo
        try:
            self.img_label.configure(image=photo)
            self.img_label.image = photo
        except Exception:
            pass
        self.on_image_loaded(self.item.get("id", ""), url)

    def mark_seen(self):
        self._bg = COLORS["card_seen"]
        self._set_bg(self._bg)
        self.item["seen"] = 1
        # حذف dot
        for w in self.winfo_children():
            if isinstance(w, tk.Label) and w.cget("text") == "●":
                w.destroy()


# ---------------------------------------------------------------------------
# پنجره اسکنر DNS
# ---------------------------------------------------------------------------

class DNSScannerWindow(tk.Toplevel):
    def __init__(self, parent, on_select_cb):
        super().__init__(parent)
        self.title("اسکنر DNS")
        self.geometry("700x520")
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)
        self.on_select_cb = on_select_cb
        self._results = []

        self._build()
        self.after(200, self._start_scan)

    def _build(self):
        # هدر
        hdr = tk.Frame(self, bg=COLORS["sidebar"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍  اسکنر DNS", font=FONT_LARGE,
                 fg=COLORS["text_primary"], bg=COLORS["sidebar"]).pack(side="left", padx=16)

        self.progress_var = tk.StringVar(value="در حال اسکن...")
        tk.Label(hdr, textvariable=self.progress_var, font=FONT_SUMMARY,
                 fg=COLORS["text_secondary"], bg=COLORS["sidebar"]).pack(side="right", padx=16)

        # تست فیلتر سایت‌ها
        site_frame = tk.Frame(self, bg=COLORS["panel"], pady=6)
        site_frame.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(site_frame, text="سایت‌های تست فیلتر:", font=FONT_BTN,
                 fg=COLORS["text_secondary"], bg=COLORS["panel"]).pack(side="left", padx=8)
        self.site_vars = {}
        for s in config.FILTER_TEST_SITES:
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(site_frame, text=s.replace("www.", ""),
                                variable=var, font=FONT_META,
                                fg=COLORS["text_secondary"], bg=COLORS["panel"],
                                selectcolor=COLORS["input_bg"],
                                activebackground=COLORS["panel"])
            cb.pack(side="left", padx=2)
            self.site_vars[s] = var

        # پروگرس بار
        self.pb = ttk.Progressbar(self, mode="indeterminate")
        self.pb.pack(fill="x", padx=8, pady=4)
        self.pb.start(12)

        # جدول نتایج
        cols = ("name", "latency", "working") + tuple(s.replace("www.", "").split(".")[0] for s in config.FILTER_TEST_SITES)
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self._style_tree()

        self.tree.heading("name",    text="سرور")
        self.tree.heading("latency", text="تاخیر (ms)")
        self.tree.heading("working", text="وضعیت")
        self.tree.column("name",    width=130, anchor="w")
        self.tree.column("latency", width=80,  anchor="center")
        self.tree.column("working", width=70,  anchor="center")
        for s in config.FILTER_TEST_SITES:
            col = s.replace("www.", "").split(".")[0]
            self.tree.heading(col, text=col)
            self.tree.column(col, width=65, anchor="center")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)

        # دکمه‌های پایین
        btn_frame = tk.Frame(self, bg=COLORS["bg"], pady=8)
        btn_frame.pack(fill="x", padx=8)

        self.use_btn = tk.Button(
            btn_frame, text="✅ استفاده از این DNS",
            font=FONT_BTN, bg=COLORS["btn"], fg="white",
            relief="flat", padx=12, pady=6,
            command=self._use_selected, state="disabled"
        )
        self.use_btn.pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="🔄 اسکن مجدد",
            font=FONT_BTN, bg=COLORS["input_bg"], fg=COLORS["text_primary"],
            relief="flat", padx=12, pady=6,
            command=self._rescan
        ).pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="✨ بهترین خودکار",
            font=FONT_BTN, bg=COLORS["accent2"], fg=COLORS["bg"],
            relief="flat", padx=12, pady=6,
            command=self._use_best
        ).pack(side="right", padx=4)

        self.tree.bind("<<TreeviewSelect>>", lambda e: self.use_btn.config(state="normal"))

    def _style_tree(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                         background=COLORS["card"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["card"],
                         rowheight=28,
                         font=FONT_SUMMARY)
        style.configure("Treeview.Heading",
                         background=COLORS["sidebar"],
                         foreground=COLORS["text_secondary"],
                         font=FONT_BTN)
        style.map("Treeview", background=[("selected", COLORS["accent"])])

    def _start_scan(self):
        self.tree.delete(*self.tree.get_children())
        self._results = []
        selected_sites = [s for s, v in self.site_vars.items() if v.get()]
        self.pb.start(12)
        self.progress_var.set("در حال اسکن...")

        def scan():
            scanner = core.DNSScanner()
            results = scanner.scan_all(
                config.DOH_SERVERS, selected_sites,
                progress_cb=lambda r: self.after(0, self._add_row, r)
            )
            self._results = results
            self.after(0, self._scan_done, results)

        threading.Thread(target=scan, daemon=True).start()

    def _add_row(self, r: dict):
        selected_sites = [s for s, v in self.site_vars.items() if v.get()]
        latency = f"{r['latency_ms']} ms" if r["latency_ms"] else "—"
        working = "✅" if r["working"] else "❌"
        filter_vals = []
        for s in selected_sites:
            v = r["filters"].get(s)
            if v is None:
                filter_vals.append("?")
            elif v:
                filter_vals.append("🔴")
            else:
                filter_vals.append("🟢")

        row = (r["name"], latency, working) + tuple(filter_vals)
        tag = "working" if r["working"] else "dead"
        self.tree.insert("", "end", iid=r["ip"], values=row, tags=(tag,))
        self.tree.tag_configure("working", foreground=COLORS["text_primary"])
        self.tree.tag_configure("dead",    foreground=COLORS["text_seen"])

    def _scan_done(self, results):
        self.pb.stop()
        done = sum(1 for r in results if r["working"])
        self.progress_var.set(f"اتمام اسکن — {done}/{len(results)} سرور فعال")

    def _rescan(self):
        self._start_scan()

    def _use_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        ip = sel[0]
        srv = next((r for r in self._results if r["ip"] == ip), None)
        if srv:
            self.on_select_cb(srv)
            self.destroy()

    def _use_best(self):
        if not self._results:
            messagebox.showwarning("صبر کن", "اسکن هنوز تموم نشده!", parent=self)
            return
        scanner = core.DNSScanner()
        best = scanner.best_server(self._results)
        if best:
            self.on_select_cb(best)
            self.destroy()
        else:
            messagebox.showerror("خطا", "هیچ سرور فعالی پیدا نشد.", parent=self)


# ---------------------------------------------------------------------------
# پنجره جزئیات خبر
# ---------------------------------------------------------------------------

class NewsDetailWindow(tk.Toplevel):
    def __init__(self, parent, item: dict):
        super().__init__(parent)
        self.title(item.get("title", "خبر"))
        self.geometry("680x540")
        self.configure(bg=COLORS["bg"])
        self._item = item
        self._build()

    def _build(self):
        item = self._item

        # تصویر بالا (اگه داشت)
        if PIL_OK and item.get("image_url"):
            def load_img():
                data = core.fetch_image_bytes(item["image_url"])
                if data:
                    photo = resize_image(data, 660, 200)
                    if photo:
                        self.after(0, self._set_hero, photo)
            threading.Thread(target=load_img, daemon=True).start()

        self.hero_frame = tk.Frame(self, bg=COLORS["sidebar"], height=8)
        self.hero_frame.pack(fill="x")

        # محتوا
        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(content, text=item.get("title", ""), font=("Tahoma", 13, "bold"),
                 fg=COLORS["text_primary"], bg=COLORS["bg"],
                 wraplength=640, justify="left", anchor="w").pack(anchor="w")

        meta = f"📅 {item.get('published', '')[:16]}"
        tk.Label(content, text=meta, font=FONT_META,
                 fg=COLORS["text_secondary"], bg=COLORS["bg"]).pack(anchor="w", pady=(4, 12))

        sep = tk.Frame(content, height=1, bg=COLORS["separator"])
        sep.pack(fill="x", pady=(0, 12))

        # خلاصه
        txt = tk.Text(content, font=FONT_SUMMARY, fg=COLORS["text_primary"],
                      bg=COLORS["card"], relief="flat", wrap="word",
                      height=8, padx=12, pady=10)
        txt.insert("1.0", item.get("summary", "خلاصه‌ای موجود نیست."))
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True)

        # دکمه‌ها
        btn_row = tk.Frame(self, bg=COLORS["bg"], pady=12)
        btn_row.pack(fill="x", padx=20)

        tk.Button(
            btn_row, text="🔗 باز کردن در مرورگر",
            font=FONT_BTN, bg=COLORS["btn"], fg="white",
            relief="flat", padx=16, pady=8,
            command=lambda: webbrowser.open(item.get("link", ""))
        ).pack(side="left")

        tk.Button(
            btn_row, text="✕ بستن",
            font=FONT_BTN, bg=COLORS["input_bg"], fg=COLORS["text_primary"],
            relief="flat", padx=16, pady=8,
            command=self.destroy
        ).pack(side="right")

    def _set_hero(self, photo):
        self.hero_frame.configure(height=200)
        lbl = tk.Label(self.hero_frame, image=photo, bg=COLORS["sidebar"])
        lbl.image = photo
        lbl.pack(fill="both", expand=True)


# ---------------------------------------------------------------------------
# برنامه اصلی
# ---------------------------------------------------------------------------

class RSSApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RSS خوان")
        self.root.geometry("900x640")
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(700, 500)

        self.store = core.Store(config.DB_FILE)
        self.feeds = list(config.DEFAULT_FEEDS)
        self._active_feed = None
        self._cards: list[NewsCard] = []
        self._image_queue = queue.Queue()

        # نصب DoH پیش‌فرض
        doh = config.ACTIVE_DOH
        core.install_doh_resolver(doh["ip"], doh["host"])

        self._apply_style()
        self._build_layout()
        self._refresh_sidebar()
        self._start_bg_threads()

    # ---- استایل کلی ----
    def _apply_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TScrollbar",
                         background=COLORS["sidebar"],
                         troughcolor=COLORS["bg"],
                         arrowcolor=COLORS["text_secondary"])

    # ---- ساخت چیدمان ----
    def _build_layout(self):
        # نوار کناری چپ
        self.sidebar = tk.Frame(self.root, bg=COLORS["sidebar"], width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # محتوای اصلی
        self.main = tk.Frame(self.root, bg=COLORS["bg"])
        self.main.pack(side="left", fill="both", expand=True)
        self._build_main()

    def _build_sidebar(self):
        # لوگو
        logo = tk.Frame(self.sidebar, bg=COLORS["sidebar"], pady=16)
        logo.pack(fill="x")
        tk.Label(logo, text="📡 RSS خوان", font=FONT_LARGE,
                 fg=COLORS["text_primary"], bg=COLORS["sidebar"]).pack(side="left", padx=14)

        sep = tk.Frame(self.sidebar, height=1, bg=COLORS["bg"])
        sep.pack(fill="x")

        # دکمه‌های ابزار
        tools = tk.Frame(self.sidebar, bg=COLORS["sidebar"], pady=6)
        tools.pack(fill="x", padx=8)

        self._sidebar_btn("🔍 اسکنر DNS", self._open_dns_scanner, tools)
        self._sidebar_btn("➕ افزودن فید", self._add_feed, tools)
        self._sidebar_btn("🔄 چک همه", self._check_all, tools)

        sep2 = tk.Frame(self.sidebar, height=1, bg=COLORS["bg"])
        sep2.pack(fill="x", pady=4)

        tk.Label(self.sidebar, text="فیدها", font=FONT_META,
                 fg=COLORS["text_secondary"], bg=COLORS["sidebar"]).pack(anchor="w", padx=14, pady=(4, 2))

        # لیست فیدها (اسکرول‌پذیر)
        self.feed_list_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar"])
        self.feed_list_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(self.feed_list_frame, bg=COLORS["sidebar"],
                           highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(self.feed_list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._feed_inner = tk.Frame(canvas, bg=COLORS["sidebar"])
        self._feed_canvas_window = canvas.create_window((0, 0), window=self._feed_inner, anchor="nw")
        self._feed_inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            self._feed_canvas_window, width=e.width))
        self._feed_canvas = canvas

        # نوار وضعیت پایین sidebar
        self.dns_status = tk.Label(self.sidebar, text=f"DNS: {config.ACTIVE_DOH['name']}",
                                   font=FONT_META, fg=COLORS["text_secondary"],
                                   bg=COLORS["sidebar"])
        self.dns_status.pack(side="bottom", anchor="w", padx=10, pady=6)

    def _sidebar_btn(self, text, cmd, parent):
        btn = tk.Button(
            parent, text=text, font=FONT_BTN,
            bg=COLORS["sidebar"], fg=COLORS["text_primary"],
            relief="flat", anchor="w", padx=10, pady=7,
            activebackground=COLORS["card_hover"],
            activeforeground=COLORS["text_primary"],
            command=cmd
        )
        btn.pack(fill="x", pady=1)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=COLORS["card_hover"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=COLORS["sidebar"]))

    def _build_main(self):
        # هدر
        self.header = tk.Frame(self.main, bg=COLORS["sidebar"], pady=12)
        self.header.pack(fill="x")

        self.header_title = tk.Label(
            self.header, text="همه اخبار", font=FONT_LARGE,
            fg=COLORS["text_primary"], bg=COLORS["sidebar"]
        )
        self.header_title.pack(side="left", padx=16)

        self.header_count = tk.Label(
            self.header, text="", font=FONT_META,
            fg=COLORS["text_secondary"], bg=COLORS["sidebar"]
        )
        self.header_count.pack(side="right", padx=16)

        # فیلتر خوانده‌شده
        self.show_seen_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            self.header, text="نمایش خوانده‌شده",
            variable=self.show_seen_var,
            font=FONT_BTN, fg=COLORS["text_secondary"],
            bg=COLORS["sidebar"], selectcolor=COLORS["input_bg"],
            activebackground=COLORS["sidebar"],
            command=self._reload_cards
        ).pack(side="right", padx=8)

        # نوار جستجو
        search_row = tk.Frame(self.main, bg=COLORS["panel"], pady=6)
        search_row.pack(fill="x", padx=0)
        tk.Label(search_row, text="🔎", fg=COLORS["text_secondary"],
                 bg=COLORS["panel"]).pack(side="left", padx=(12, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._reload_cards())
        tk.Entry(search_row, textvariable=self.search_var,
                 font=FONT_SUMMARY, bg=COLORS["input_bg"],
                 fg=COLORS["text_primary"], relief="flat",
                 insertbackground=COLORS["text_primary"]).pack(
                     side="left", fill="x", expand=True, padx=(0, 12), ipady=4)

        # ناحیه اسکرول خبرها
        news_container = tk.Frame(self.main, bg=COLORS["bg"])
        news_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(news_container, bg=COLORS["bg"],
                                highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(news_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.cards_frame = tk.Frame(self.canvas, bg=COLORS["bg"])
        self._cards_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._cards_window, width=e.width))

        # اسکرول با موس
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # نوار وضعیت
        self.status = tk.Label(self.main, text="آماده", font=FONT_META,
                                fg=COLORS["text_secondary"], bg=COLORS["sidebar"],
                                relief="flat", anchor="e")
        self.status.pack(fill="x", side="bottom")

    # ---- فیدها در sidebar ----
    def _refresh_sidebar(self):
        for w in self._feed_inner.winfo_children():
            w.destroy()

        # آیتم "همه"
        self._feed_item_btn("📰 همه اخبار", None)

        for url in self.feeds:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc or url[:30]
            self._feed_item_btn(f"📄 {domain}", url)

    def _feed_item_btn(self, text, url):
        is_active = (url == self._active_feed)
        bg = COLORS["accent"] if is_active else COLORS["sidebar"]
        btn = tk.Button(
            self._feed_inner, text=text, font=FONT_BTN,
            bg=bg, fg=COLORS["text_primary"],
            relief="flat", anchor="w", padx=14, pady=7,
            activebackground=COLORS["card_hover"],
            command=lambda u=url: self._select_feed(u)
        )
        btn.pack(fill="x")

        # دکمه حذف
        if url:
            del_btn = tk.Button(
                self._feed_inner, text="✕", font=("", 7),
                bg=COLORS["sidebar"], fg=COLORS["text_seen"],
                relief="flat", padx=2,
                command=lambda u=url: self._del_feed(u)
            )
            del_btn.place_forget()
            btn.bind("<Enter>", lambda e, b=btn, d=del_btn: (
                b.configure(bg=COLORS["card_hover"]),
            ))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(
                bg=COLORS["accent"] if (url == self._active_feed) else COLORS["sidebar"]))

    def _select_feed(self, url):
        self._active_feed = url
        title = "همه اخبار" if url is None else url
        self.header_title.configure(text=title if url is None else
            __import__("urllib.parse", fromlist=["urlparse"]).urlparse(url).netloc)
        self._refresh_sidebar()
        self._reload_cards()
        if url:
            self._set_status(f"در حال دریافت: {url}")
            threading.Thread(target=self._fetch_and_show, args=(url,), daemon=True).start()

    def _fetch_and_show(self, url):
        items = core.fetch_feed(url)
        for it in items:
            self.store.upsert(it, url)
        self.root.after(0, self._reload_cards)
        self.root.after(0, lambda: self._set_status(f"{len(items)} خبر از {url}"))

    # ---- نمایش کارت‌ها ----
    def _reload_cards(self):
        query = self.search_var.get().strip().lower()
        show_seen = self.show_seen_var.get()

        items = self.store.get_items(self._active_feed)

        if not show_seen:
            items = [i for i in items if not i.get("seen")]
        if query:
            items = [i for i in items if query in i.get("title", "").lower()
                     or query in i.get("summary", "").lower()]

        # پاک کردن کارت‌های قبلی
        for w in self.cards_frame.winfo_children():
            w.destroy()
        self._cards = []

        if not items:
            tk.Label(self.cards_frame, text="خبری برای نمایش نیست.",
                     font=FONT_SUMMARY, fg=COLORS["text_secondary"],
                     bg=COLORS["bg"]).pack(pady=60)
        else:
            for item in items:
                card = NewsCard(
                    self.cards_frame, item,
                    on_click=self._open_item,
                    on_image_loaded=self._on_image_loaded,
                )
                card.pack(fill="x")
                self._cards.append(card)

        total = len(items)
        unseen = sum(1 for i in items if not i.get("seen"))
        self.header_count.configure(
            text=f"{unseen} نخوانده / {total} مجموع" if unseen else f"{total} خبر"
        )

    def _open_item(self, item: dict):
        # mark seen
        self.store.mark_seen(item["id"])
        item["seen"] = 1
        for card in self._cards:
            if card.item.get("id") == item["id"]:
                card.mark_seen()
                break
        # باز کردن پنجره جزئیات
        NewsDetailWindow(self.root, item)
        # آپدیت شمارنده
        unseen = sum(1 for c in self._cards if not c.item.get("seen"))
        total = len(self._cards)
        self.header_count.configure(
            text=f"{unseen} نخوانده / {total} مجموع" if unseen else f"{total} خبر"
        )

    def _on_image_loaded(self, item_id: str, url: str):
        if item_id and url:
            self.store.update_image(item_id, url)

    # ---- عملیات فید ----
    def _add_feed(self):
        url = simpledialog.askstring("افزودن فید", "آدرس RSS را وارد کنید:", parent=self.root)
        if url and url.strip():
            url = url.strip()
            if url not in self.feeds:
                self.feeds.append(url)
                self._refresh_sidebar()
                self._select_feed(url)

    def _del_feed(self, url):
        if url in self.feeds:
            self.feeds.remove(url)
            if self._active_feed == url:
                self._active_feed = None
            self._refresh_sidebar()
            self._reload_cards()

    def _check_all(self):
        self._set_status("بررسی همه فیدها...")
        def worker():
            for url in self.feeds:
                items = core.fetch_feed(url)
                for it in items:
                    self.store.upsert(it, url)
                time.sleep(0.5)
            self.root.after(0, self._reload_cards)
            self.root.after(0, lambda: self._set_status("بررسی همه فیدها انجام شد."))
        threading.Thread(target=worker, daemon=True).start()

    # ---- DNS اسکنر ----
    def _open_dns_scanner(self):
        DNSScannerWindow(self.root, self._apply_dns)

    def _apply_dns(self, server: dict):
        config.ACTIVE_DOH = server
        core.install_doh_resolver(server["ip"], server["host"])
        self.dns_status.configure(text=f"DNS: {server['name']} ({server['latency_ms']} ms)")
        self._set_status(f"✅ DNS تغییر کرد به {server['name']}")

    # ---- وضعیت ----
    def _set_status(self, msg: str):
        self.status.configure(text=msg)

    # ---- threadهای پس‌زمینه ----
    def _start_bg_threads(self):
        # بارگذاری اولیه
        threading.Thread(target=self._initial_load, daemon=True).start()
        # auto-check
        if config.CHECK_INTERVAL > 0:
            def auto():
                while True:
                    time.sleep(config.CHECK_INTERVAL)
                    for url in self.feeds:
                        items = core.fetch_feed(url)
                        for it in items:
                            self.store.upsert(it, url)
                    self.root.after(0, self._reload_cards)
            threading.Thread(target=auto, daemon=True).start()

    def _initial_load(self):
        self._set_status("در حال دریافت فیدها...")
        for url in self.feeds:
            items = core.fetch_feed(url)
            for it in items:
                self.store.upsert(it, url)
        self.root.after(0, self._reload_cards)
        self.root.after(0, lambda: self._set_status("آماده"))


# ---------------------------------------------------------------------------
# اجرا
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import tkinter.simpledialog
    root = tk.Tk()
    try:
        root.tk.call("font", "configure", "TkDefaultFont", "-family", "Tahoma")
    except Exception:
        pass
    app = RSSApp(root)
    root.mainloop()
