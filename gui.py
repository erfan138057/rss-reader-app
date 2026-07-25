"""
gui.py - رابط کاربری RSS خوان (تم تلگرام + ردیت)
"""
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading
import time
import webbrowser
import io
import json

try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

import core
import config

# ---------------------------------------------------------------------------
# تم‌ها
# ---------------------------------------------------------------------------

THEMES = {
    "dark": {
        "bg":            "#17212B",
        "sidebar":       "#0E1621",
        "card":          "#1E2C3A",
        "card_seen":     "#17212B",
        "card_hover":    "#243447",
        "accent":        "#2196F3",
        "accent2":       "#64B5F6",
        "text_primary":  "#FFFFFF",
        "text_secondary":"#7B8EA0",
        "text_seen":     "#5B6C7D",
        "badge":         "#2196F3",
        "separator":     "#0E1621",
        "input_bg":      "#242F3D",
        "btn":           "#2196F3",
        "btn_hover":     "#1976D2",
        "danger":        "#E53935",
        "success":       "#43A047",
        "warning":       "#FB8C00",
        "panel":         "#1C2A38",
        "reddit_header": "#1A2839",
        "reddit_card":   "#1E2C3A",
        "reddit_vote":   "#243447",
        "reddit_border": "#2A3D52",
    },
    "light": {
        "bg":            "#F6F7F8",
        "sidebar":       "#FFFFFF",
        "card":          "#FFFFFF",
        "card_seen":     "#F0F2F5",
        "card_hover":    "#E8EDF2",
        "accent":        "#0079D3",
        "accent2":       "#1484D6",
        "text_primary":  "#1C1C1C",
        "text_secondary":"#7C7C7C",
        "text_seen":     "#AAAAAA",
        "badge":         "#0079D3",
        "separator":     "#EDEFF1",
        "input_bg":      "#EDEFF1",
        "btn":           "#0079D3",
        "btn_hover":     "#006BBD",
        "danger":        "#E53935",
        "success":       "#43A047",
        "warning":       "#FB8C00",
        "panel":         "#EDEFF1",
        "reddit_header": "#FFFFFF",
        "reddit_card":   "#FFFFFF",
        "reddit_vote":   "#F8F9FA",
        "reddit_border": "#EDEFF1",
    },
}

C = THEMES["dark"]   # رنگ فعال

FONT_TITLE   = ("Tahoma", 10, "bold")
FONT_SUMMARY = ("Tahoma", 9)
FONT_META    = ("Tahoma", 8)
FONT_LARGE   = ("Tahoma", 12, "bold")
FONT_BTN     = ("Tahoma", 9)
FONT_MONO    = ("Courier New", 9)

# ---------------------------------------------------------------------------
# ابزارهای UI
# ---------------------------------------------------------------------------

def make_placeholder(w=80, h=60):
    if not PIL_OK:
        return None
    img = Image.new("RGB", (w, h), C["card_hover"])
    draw = ImageDraw.Draw(img)
    draw.rectangle([w//4, h//4, 3*w//4, 3*h//4], outline=C["text_seen"], width=1)
    draw.line([w//4, h//4, 3*w//4, 3*h//4], fill=C["text_seen"], width=1)
    draw.line([3*w//4, h//4, w//4, 3*h//4], fill=C["text_seen"], width=1)
    return ImageTk.PhotoImage(img)


def resize_image(data: bytes, w: int, h: int):
    if not PIL_OK or not data:
        return None
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.thumbnail((w, h), Image.LANCZOS)
        iw, ih = img.size
        left = (iw - min(iw, w)) // 2
        top  = (ih - min(ih, h)) // 2
        img = img.crop((left, top, left + min(iw, w), top + min(ih, h)))
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def apply_theme_to(widget, bg=None, fg=None, recursive=True):
    try:
        kw = {}
        if bg: kw["bg"] = bg
        if fg: kw["fg"] = fg
        widget.configure(**kw)
    except Exception:
        pass
    if recursive:
        for child in widget.winfo_children():
            apply_theme_to(child, bg, fg, True)

# ---------------------------------------------------------------------------
# کارت خبر (حالت پیش‌فرض — telegram style)
# ---------------------------------------------------------------------------

class NewsCard(tk.Frame):
    TW, TH = 80, 60

    def __init__(self, master, item: dict, on_click, on_image_loaded, **kw):
        seen = bool(item.get("seen"))
        bg = C["card_seen"] if seen else C["card"]
        super().__init__(master, bg=bg, cursor="hand2", **kw)
        self.item = item
        self.on_click = on_click
        self.on_image_loaded = on_image_loaded
        self._bg = bg
        self._photo = None
        self._placeholder = make_placeholder(self.TW, self.TH)
        self._build()
        self._bind_all()
        self._load_image_async()

    def _build(self):
        seen = bool(self.item.get("seen"))
        tc = C["text_seen"] if seen else C["text_primary"]
        mc = C["text_seen"] if seen else C["text_secondary"]

        self.img_lbl = tk.Label(self, bg=self._bg, image=self._placeholder,
                                 width=self.TW, height=self.TH)
        self.img_lbl.image = self._placeholder
        self.img_lbl.pack(side="left", padx=(10, 8), pady=8)

        tf = tk.Frame(self, bg=self._bg)
        tf.pack(side="left", fill="both", expand=True, pady=8, padx=(0, 8))

        tk.Label(tf, text=self.item.get("title", ""), font=FONT_TITLE,
                  fg=tc, bg=self._bg, anchor="w", justify="left",
                  wraplength=420).pack(anchor="w")

        sm = self.item.get("summary", "")
        if sm:
            tk.Label(tf, text=sm[:120] + ("…" if len(sm) > 120 else ""),
                      font=FONT_SUMMARY, fg=mc, bg=self._bg,
                      anchor="w", justify="left", wraplength=420).pack(anchor="w", pady=(2, 0))

        pub = self.item.get("published", "")
        from urllib.parse import urlparse as up
        domain = up(self.item.get("feed", "")).netloc
        meta = f"{pub[:16]}  •  {domain}" if domain else pub[:16]
        tk.Label(tf, text=meta, font=FONT_META, fg=mc, bg=self._bg,
                  anchor="w").pack(anchor="w", pady=(3, 0))

        if not seen:
            tk.Label(self, text="●", fg=C["badge"], bg=self._bg,
                      font=("", 8)).pack(side="right", padx=8)

        tk.Frame(self, height=1, bg=C["separator"]).pack(side="bottom", fill="x")

        for w in tf.winfo_children():
            self._bind_w(w)

    def _bind_all(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Enter>", lambda e: self._set_bg(C["card_hover"]))
        self.bind("<Leave>", lambda e: self._set_bg(self._bg))
        for w in self.winfo_children():
            self._bind_w(w)

    def _bind_w(self, w):
        w.bind("<Button-1>", self._clicked)
        w.bind("<Enter>", lambda e: self._set_bg(C["card_hover"]))
        w.bind("<Leave>", lambda e: self._set_bg(self._bg))

    def _set_bg(self, color):
        self.configure(bg=color)
        for w in self.winfo_children():
            try: w.configure(bg=color)
            except: pass

    def _clicked(self, e=None):
        self.on_click(self.item)

    def _load_image_async(self):
        def worker():
            url = self.item.get("image_url", "")
            data = core.fetch_image_bytes(url) if url else None
            if not data and self.item.get("link"):
                og = core.fetch_og_image(self.item["link"])
                if og:
                    self.item["image_url"] = og
                    data = core.fetch_image_bytes(og)
            if data:
                photo = resize_image(data, self.TW, self.TH)
                if photo:
                    self.after(0, self._set_img, photo)
        threading.Thread(target=worker, daemon=True).start()

    def _set_img(self, photo):
        self._photo = photo
        try:
            self.img_lbl.configure(image=photo)
            self.img_lbl.image = photo
        except Exception:
            pass
        self.on_image_loaded(self.item.get("id", ""), self.item.get("image_url", ""))

    def mark_seen(self):
        self._bg = C["card_seen"]
        self._set_bg(self._bg)
        self.item["seen"] = 1
        for w in self.winfo_children():
            if isinstance(w, tk.Label) and w.cget("text") == "●":
                w.destroy()

# ---------------------------------------------------------------------------
# صفحه ردیت برای هر فید
# ---------------------------------------------------------------------------

class RedditCard(tk.Frame):
    """کارت خبر به سبک ردیت — افقی، تصویر بزرگ‌تر."""
    IW, IH = 140, 90

    def __init__(self, master, item: dict, index: int, on_click, on_image_loaded, **kw):
        bg = C["reddit_card"]
        super().__init__(master, bg=bg, cursor="hand2",
                          relief="flat", bd=0, **kw)
        self.item = item
        self.index = index
        self.on_click = on_click
        self.on_image_loaded = on_image_loaded
        self._bg = bg
        self._photo = None
        self._build()
        self._bind_all()
        self._load_image_async()

    def _build(self):
        seen = bool(self.item.get("seen"))
        tc = C["text_seen"] if seen else C["text_primary"]
        mc = C["text_secondary"]

        # شماره
        tk.Label(self, text=f"{self.index}.", font=FONT_META,
                  fg=C["text_secondary"], bg=self._bg,
                  width=3).pack(side="left", padx=(6, 2), pady=10, anchor="n")

        # تصویر
        ph = make_placeholder(self.IW, self.IH)
        self.img_lbl = tk.Label(self, bg=self._bg, image=ph,
                                 width=self.IW, height=self.IH)
        self.img_lbl.image = ph
        self.img_lbl.pack(side="left", padx=(4, 10), pady=10, anchor="n")

        # محتوا
        tf = tk.Frame(self, bg=self._bg)
        tf.pack(side="left", fill="both", expand=True, pady=10, padx=(0, 10))

        tk.Label(tf, text=self.item.get("title", ""), font=FONT_TITLE,
                  fg=tc, bg=self._bg, anchor="w", justify="left",
                  wraplength=460).pack(anchor="w")

        sm = self.item.get("summary", "")
        if sm:
            tk.Label(tf, text=sm[:180] + ("…" if len(sm) > 180 else ""),
                      font=FONT_SUMMARY, fg=mc, bg=self._bg,
                      anchor="w", justify="left", wraplength=460).pack(anchor="w", pady=(3, 0))

        pub = self.item.get("published", "")
        from urllib.parse import urlparse as up
        domain = up(self.item.get("feed", "")).netloc
        meta = f"📅 {pub[:16]}   🌐 {domain}" if domain else f"📅 {pub[:16]}"
        tk.Label(tf, text=meta, font=FONT_META, fg=C["text_secondary"],
                  bg=self._bg, anchor="w").pack(anchor="w", pady=(5, 0))

        # خط جدا
        tk.Frame(self, height=1, bg=C["reddit_border"]).pack(side="bottom", fill="x")

        for w in tf.winfo_children():
            self._bind_w(w)

    def _bind_all(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Enter>", lambda e: self._set_bg(C["card_hover"]))
        self.bind("<Leave>", lambda e: self._set_bg(self._bg))
        for w in self.winfo_children():
            self._bind_w(w)

    def _bind_w(self, w):
        w.bind("<Button-1>", self._clicked)
        w.bind("<Enter>", lambda e: self._set_bg(C["card_hover"]))
        w.bind("<Leave>", lambda e: self._set_bg(self._bg))

    def _set_bg(self, color):
        self.configure(bg=color)
        for w in self.winfo_children():
            try: w.configure(bg=color)
            except: pass

    def _clicked(self, e=None):
        self.on_click(self.item)

    def _load_image_async(self):
        def worker():
            url = self.item.get("image_url", "")
            data = core.fetch_image_bytes(url) if url else None
            if not data and self.item.get("link"):
                og = core.fetch_og_image(self.item["link"])
                if og:
                    self.item["image_url"] = og
                    data = core.fetch_image_bytes(og)
            if data:
                photo = resize_image(data, self.IW, self.IH)
                if photo:
                    self.after(0, self._set_img, photo)
        threading.Thread(target=worker, daemon=True).start()

    def _set_img(self, photo):
        self._photo = photo
        try:
            self.img_lbl.configure(image=photo)
            self.img_lbl.image = photo
        except Exception:
            pass
        self.on_image_loaded(self.item.get("id", ""), self.item.get("image_url", ""))

# ---------------------------------------------------------------------------
# پنجره جزئیات خبر
# ---------------------------------------------------------------------------

class NewsDetailWindow(tk.Toplevel):
    def __init__(self, parent, item: dict):
        super().__init__(parent)
        self.title(item.get("title", "خبر"))
        self.geometry("700x560")
        self.configure(bg=C["bg"])
        self._item = item
        self._build()

    def _build(self):
        item = self._item
        self.hero_frame = tk.Frame(self, bg=C["sidebar"], height=8)
        self.hero_frame.pack(fill="x")

        if PIL_OK and item.get("image_url"):
            def load():
                data = core.fetch_image_bytes(item["image_url"])
                if data:
                    photo = resize_image(data, 680, 200)
                    if photo:
                        self.after(0, self._set_hero, photo)
            threading.Thread(target=load, daemon=True).start()

        content = tk.Frame(self, bg=C["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(content, text=item.get("title", ""), font=("Tahoma", 13, "bold"),
                  fg=C["text_primary"], bg=C["bg"],
                  wraplength=660, justify="left", anchor="w").pack(anchor="w")

        tk.Label(content, text=f"📅 {item.get('published','')[:16]}",
                  font=FONT_META, fg=C["text_secondary"], bg=C["bg"]).pack(anchor="w", pady=(4,12))

        tk.Frame(content, height=1, bg=C["separator"]).pack(fill="x", pady=(0,12))

        txt = tk.Text(content, font=FONT_SUMMARY, fg=C["text_primary"],
                       bg=C["card"], relief="flat", wrap="word",
                       height=8, padx=12, pady=10)
        txt.insert("1.0", item.get("summary", "خلاصه‌ای موجود نیست."))
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True)

        btn_row = tk.Frame(self, bg=C["bg"], pady=12)
        btn_row.pack(fill="x", padx=20)
        tk.Button(btn_row, text="🔗 باز کردن در مرورگر",
                   font=FONT_BTN, bg=C["btn"], fg="white", relief="flat",
                   padx=16, pady=8,
                   command=lambda: webbrowser.open(item.get("link",""))
                   ).pack(side="left")
        tk.Button(btn_row, text="✕ بستن",
                   font=FONT_BTN, bg=C["input_bg"], fg=C["text_primary"],
                   relief="flat", padx=16, pady=8,
                   command=self.destroy).pack(side="right")

    def _set_hero(self, photo):
        self.hero_frame.configure(height=200)
        lbl = tk.Label(self.hero_frame, image=photo, bg=C["sidebar"])
        lbl.image = photo
        lbl.pack(fill="both", expand=True)

# ---------------------------------------------------------------------------
# پنجره DNS اسکنر
# ---------------------------------------------------------------------------

class DNSScannerWindow(tk.Toplevel):
    def __init__(self, parent, on_select_cb, store):
        super().__init__(parent)
        self.title("اسکنر DNS")
        self.geometry("760x580")
        self.configure(bg=C["bg"])
        self.on_select_cb = on_select_cb
        self.store = store
        self._results = []
        self._build()
        self.after(200, self._start_scan)

    def _build(self):
        hdr = tk.Frame(self, bg=C["sidebar"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍  اسکنر DNS", font=FONT_LARGE,
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=16)
        self.prog_var = tk.StringVar(value="در حال اسکن...")
        tk.Label(hdr, textvariable=self.prog_var, font=FONT_SUMMARY,
                  fg=C["text_secondary"], bg=C["sidebar"]).pack(side="right", padx=16)

        # افزودن DNS دستی
        add_frame = tk.Frame(self, bg=C["panel"], pady=6)
        add_frame.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(add_frame, text="➕ DNS دستی:", font=FONT_BTN,
                  fg=C["text_secondary"], bg=C["panel"]).pack(side="left", padx=8)
        self.custom_name = tk.Entry(add_frame, width=10, font=FONT_SUMMARY,
                                     bg=C["input_bg"], fg=C["text_primary"],
                                     relief="flat", insertbackground=C["text_primary"])
        self.custom_name.insert(0, "نام")
        self.custom_name.pack(side="left", padx=4, ipady=3)
        self.custom_ip = tk.Entry(add_frame, width=15, font=FONT_MONO,
                                   bg=C["input_bg"], fg=C["text_primary"],
                                   relief="flat", insertbackground=C["text_primary"])
        self.custom_ip.insert(0, "IP (مثل 1.1.1.1)")
        self.custom_ip.pack(side="left", padx=4, ipady=3)
        self.custom_host = tk.Entry(add_frame, width=20, font=FONT_MONO,
                                     bg=C["input_bg"], fg=C["text_primary"],
                                     relief="flat", insertbackground=C["text_primary"])
        self.custom_host.insert(0, "host (مثل cloudflare-dns.com)")
        self.custom_host.pack(side="left", padx=4, ipady=3)
        tk.Button(add_frame, text="اضافه کن", font=FONT_BTN,
                   bg=C["btn"], fg="white", relief="flat", padx=8, pady=3,
                   command=self._add_custom_dns).pack(side="left", padx=6)

        self.pb = ttk.Progressbar(self, mode="indeterminate")
        self.pb.pack(fill="x", padx=8, pady=4)
        self.pb.start(12)

        cols = ("name", "ip", "latency", "working") + \
               tuple(s.replace("www.", "").split(".")[0] for s in config.FILTER_TEST_SITES)
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self._style_tree()

        self.tree.heading("name",    text="سرور")
        self.tree.heading("ip",      text="IP")
        self.tree.heading("latency", text="تأخیر")
        self.tree.heading("working", text="وضعیت")
        self.tree.column("name",    width=120, anchor="w")
        self.tree.column("ip",      width=110, anchor="center")
        self.tree.column("latency", width=70,  anchor="center")
        self.tree.column("working", width=60,  anchor="center")
        for s in config.FILTER_TEST_SITES:
            col = s.replace("www.", "").split(".")[0]
            self.tree.heading(col, text=col)
            self.tree.column(col, width=60, anchor="center")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8,0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)

        btn_frame = tk.Frame(self, bg=C["bg"], pady=8)
        btn_frame.pack(fill="x", padx=8)

        self.use_btn = tk.Button(btn_frame, text="✅ استفاده از این DNS",
                                  font=FONT_BTN, bg=C["btn"], fg="white",
                                  relief="flat", padx=12, pady=6,
                                  command=self._use_selected, state="disabled")
        self.use_btn.pack(side="left", padx=4)

        tk.Button(btn_frame, text="🔄 اسکن مجدد", font=FONT_BTN,
                   bg=C["input_bg"], fg=C["text_primary"],
                   relief="flat", padx=12, pady=6,
                   command=self._start_scan).pack(side="left", padx=4)

        tk.Button(btn_frame, text="✨ بهترین خودکار", font=FONT_BTN,
                   bg=C["accent2"], fg=C["bg"],
                   relief="flat", padx=12, pady=6,
                   command=self._use_best).pack(side="right", padx=4)

        self.tree.bind("<<TreeviewSelect>>",
                        lambda e: self.use_btn.config(state="normal"))

    def _style_tree(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview", background=C["card"], foreground=C["text_primary"],
                     fieldbackground=C["card"], rowheight=28, font=FONT_SUMMARY)
        s.configure("Treeview.Heading", background=C["sidebar"],
                     foreground=C["text_secondary"], font=FONT_BTN)
        s.map("Treeview", background=[("selected", C["accent"])])

    def _add_custom_dns(self):
        name = self.custom_name.get().strip()
        ip   = self.custom_ip.get().strip()
        host = self.custom_host.get().strip()
        if not name or not ip or not host or ip == "IP (مثل 1.1.1.1)":
            messagebox.showwarning("خطا", "نام، IP و host رو کامل وارد کن.", parent=self)
            return
        new_srv = {"name": name, "ip": ip, "host": host}
        if new_srv not in config.DOH_SERVERS:
            config.DOH_SERVERS.append(new_srv)
        core.LOG.info(f"DNS دستی اضافه شد: {name} ({ip})")
        self._start_scan()

    def _start_scan(self):
        self.tree.delete(*self.tree.get_children())
        self._results = []
        self.pb.start(12)
        self.prog_var.set("در حال اسکن...")

        def scan():
            scanner = core.DNSScanner()
            results = scanner.scan_all(
                config.DOH_SERVERS, config.FILTER_TEST_SITES,
                progress_cb=lambda r: self.after(0, self._add_row, r)
            )
            self._results = results
            self.after(0, self._scan_done, results)
        threading.Thread(target=scan, daemon=True).start()

    def _add_row(self, r: dict):
        latency = f"{r['latency_ms']}ms" if r["latency_ms"] else "—"
        working = "✅" if r["working"] else "❌"
        filter_vals = []
        for s in config.FILTER_TEST_SITES:
            v = r["filters"].get(s)
            filter_vals.append("?" if v is None else ("🔴" if v else "🟢"))
        row = (r["name"], r["ip"], latency, working) + tuple(filter_vals)
        tag = "working" if r["working"] else "dead"
        try:
            self.tree.insert("", "end", iid=r["ip"], values=row, tags=(tag,))
            self.tree.tag_configure("working", foreground=C["text_primary"])
            self.tree.tag_configure("dead",    foreground=C["text_seen"])
        except Exception:
            pass

    def _scan_done(self, results):
        self.pb.stop()
        done = sum(1 for r in results if r["working"])
        self.prog_var.set(f"اتمام اسکن — {done}/{len(results)} سرور فعال")

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
        best = core.DNSScanner().best_server(self._results)
        if best:
            self.on_select_cb(best)
            self.destroy()
        else:
            messagebox.showerror("خطا", "هیچ سرور فعالی پیدا نشد.", parent=self)

# ---------------------------------------------------------------------------
# پنجره لاگ
# ---------------------------------------------------------------------------

class LogWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("لاگ برنامه")
        self.geometry("740x460")
        self.configure(bg=C["bg"])
        self._build()
        self._load_existing()
        core.LOG.add_callback(self._append_line)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        hdr = tk.Frame(self, bg=C["sidebar"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋 لاگ برنامه", font=FONT_LARGE,
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=14)
        tk.Button(hdr, text="🗑 پاک کردن", font=FONT_BTN,
                   bg=C["input_bg"], fg=C["text_primary"], relief="flat",
                   padx=10, pady=4, command=self._clear).pack(side="right", padx=10)

        self.txt = tk.Text(self, font=FONT_MONO, bg=C["card"],
                            fg=C["text_primary"], relief="flat",
                            wrap="none", state="disabled",
                            padx=8, pady=6)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.txt.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.txt.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")

        self.txt.tag_configure("ERROR", foreground=C["danger"])
        self.txt.tag_configure("WARN ", foreground=C["warning"])
        self.txt.tag_configure("INFO ", foreground=C["text_primary"])
        self.txt.tag_configure("DEBUG", foreground=C["text_seen"])

    def _load_existing(self):
        for line in core.LOG.get_lines():
            self._append_line(line)

    def _append_line(self, line: str):
        self.txt.config(state="normal")
        tag = "INFO "
        for lvl in ("ERROR", "WARN ", "DEBUG"):
            if lvl in line:
                tag = lvl
                break
        self.txt.insert("end", line + "\n", tag)
        self.txt.see("end")
        self.txt.config(state="disabled")

    def _clear(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.config(state="disabled")

    def _on_close(self):
        core.LOG.remove_callback(self._append_line)
        self.destroy()

# ---------------------------------------------------------------------------
# صفحه ردیت (نمای یک فید با مرتب‌سازی)
# ---------------------------------------------------------------------------

class RedditView(tk.Frame):
    def __init__(self, master, feed_url: str, store, on_open_item, **kw):
        super().__init__(master, bg=C["bg"], **kw)
        self.feed_url = feed_url
        self.store = store
        self.on_open_item = on_open_item
        self._sort = tk.StringVar(value="newest")
        self._cards = []
        self._build()
        self._reload()

    def _build(self):
        # هدر ردیت
        hdr = tk.Frame(self, bg=C["reddit_header"], pady=10)
        hdr.pack(fill="x")

        from urllib.parse import urlparse
        domain = urlparse(self.feed_url).netloc
        tk.Label(hdr, text=f"r/{domain}", font=FONT_LARGE,
                  fg=C["text_primary"], bg=C["reddit_header"]).pack(side="left", padx=14)

        # مرتب‌سازی
        sort_frame = tk.Frame(hdr, bg=C["reddit_header"])
        sort_frame.pack(side="right", padx=14)
        tk.Label(sort_frame, text="مرتب بر اساس:", font=FONT_BTN,
                  fg=C["text_secondary"], bg=C["reddit_header"]).pack(side="left", padx=4)
        for label, val in [("🆕 جدیدترین", "newest"), ("🕰 قدیمی‌ترین", "oldest")]:
            rb = tk.Radiobutton(sort_frame, text=label, value=val,
                                 variable=self._sort,
                                 font=FONT_BTN, fg=C["text_primary"],
                                 bg=C["reddit_header"],
                                 selectcolor=C["accent"],
                                 activebackground=C["reddit_header"],
                                 command=self._reload)
            rb.pack(side="left", padx=6)

        tk.Frame(self, height=1, bg=C["reddit_border"]).pack(fill="x")

        # اسکرول‌پذیر
        container = tk.Frame(self, bg=C["bg"])
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.inner = tk.Frame(self.canvas, bg=C["bg"])
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._win, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _reload(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._cards = []
        items = self.store.get_items(self.feed_url, sort=self._sort.get())
        if not items:
            tk.Label(self.inner, text="خبری موجود نیست — روی «چک کن» کلیک کنید.",
                      font=FONT_SUMMARY, fg=C["text_secondary"],
                      bg=C["bg"]).pack(pady=60)
            return
        for i, item in enumerate(items, 1):
            card = RedditCard(self.inner, item, i,
                               on_click=self.on_open_item,
                               on_image_loaded=lambda iid, url: None)
            card.pack(fill="x", padx=4, pady=2)
            self._cards.append(card)

    def refresh(self):
        self._reload()

# ---------------------------------------------------------------------------
# برنامه اصلی
# ---------------------------------------------------------------------------

class RSSApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RSS خوان")
        self.root.geometry("960x680")
        self.root.configure(bg=C["bg"])
        self.root.minsize(720, 520)

        self.store = core.Store(config.DB_FILE)
        self._active_feed = None
        self._view_mode = "telegram"   # "telegram" یا "reddit"
        self._sort = "newest"
        self._cards = []
        self._reddit_view = None
        self._settings = config.load_settings()
        self._theme_name = self._settings.get("theme", "dark")
        self._apply_theme(self._theme_name, rebuild=False)

        doh = config.ACTIVE_DOH
        core.install_doh_resolver(doh["ip"], doh["host"])

        # اینترنت مانیتور
        self._monitor = core.InternetMonitor(interval=60, on_update=self._on_internet_update)

        self._apply_ttk_style()
        self._build_layout()
        self._refresh_sidebar()
        self._monitor.start()
        self._start_bg_threads()

    # ---- تم ----
    def _apply_theme(self, name: str, rebuild=True):
        global C
        self._theme_name = name
        C = THEMES[name]
        self._settings["theme"] = name
        config.save_settings(self._settings)
        if rebuild:
            self._rebuild_all()

    def _rebuild_all(self):
        for w in self.root.winfo_children():
            w.destroy()
        self._apply_ttk_style()
        self.root.configure(bg=C["bg"])
        self._cards = []
        self._reddit_view = None
        self._build_layout()
        self._refresh_sidebar()

    def _apply_ttk_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TScrollbar", background=C["sidebar"],
                     troughcolor=C["bg"], arrowcolor=C["text_secondary"])

    # ---- چیدمان ----
    def _build_layout(self):
        self.sidebar = tk.Frame(self.root, bg=C["sidebar"], width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        self.main = tk.Frame(self.root, bg=C["bg"])
        self.main.pack(side="left", fill="both", expand=True)
        self._build_main()

    def _build_sidebar(self):
        # لوگو + سوئیچ تم
        logo = tk.Frame(self.sidebar, bg=C["sidebar"], pady=14)
        logo.pack(fill="x")
        tk.Label(logo, text="📡 RSS خوان", font=FONT_LARGE,
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=12)

        theme_btn_text = "☀️" if self._theme_name == "dark" else "🌙"
        self._theme_btn = tk.Button(
            logo, text=theme_btn_text, font=("", 12),
            bg=C["sidebar"], fg=C["text_primary"], relief="flat",
            command=self._toggle_theme
        )
        self._theme_btn.pack(side="right", padx=8)

        tk.Frame(self.sidebar, height=1, bg=C["bg"]).pack(fill="x")

        tools = tk.Frame(self.sidebar, bg=C["sidebar"], pady=4)
        tools.pack(fill="x", padx=6)
        self._sidebar_btn("🔍 اسکنر DNS",   self._open_dns_scanner, tools)
        self._sidebar_btn("➕ افزودن فید",   self._add_feed,         tools)
        self._sidebar_btn("🔄 چک همه فیدها", self._check_all,        tools)
        self._sidebar_btn("📋 لاگ برنامه",   self._open_log,         tools)

        tk.Frame(self.sidebar, height=1, bg=C["bg"]).pack(fill="x", pady=4)
        tk.Label(self.sidebar, text="فیدها", font=FONT_META,
                  fg=C["text_secondary"], bg=C["sidebar"]).pack(anchor="w", padx=14, pady=(2,2))

        # لیست فیدها
        feed_wrap = tk.Frame(self.sidebar, bg=C["sidebar"])
        feed_wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(feed_wrap, bg=C["sidebar"], highlightthickness=0)
        vsb = ttk.Scrollbar(feed_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._feed_inner = tk.Frame(canvas, bg=C["sidebar"])
        self._fcw = canvas.create_window((0, 0), window=self._feed_inner, anchor="nw")
        self._feed_inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._fcw, width=e.width))

        # نوار پایین (DNS + اینترنت)
        bottom = tk.Frame(self.sidebar, bg=C["sidebar"])
        bottom.pack(side="bottom", fill="x")
        self.dns_lbl = tk.Label(bottom, text=f"DNS: {config.ACTIVE_DOH['name']}",
                                 font=FONT_META, fg=C["text_secondary"],
                                 bg=C["sidebar"])
        self.dns_lbl.pack(anchor="w", padx=10, pady=(4,0))
        self.net_lbl = tk.Label(bottom, text="اینترنت: بررسی...",
                                 font=FONT_META, fg=C["text_secondary"],
                                 bg=C["sidebar"])
        self.net_lbl.pack(anchor="w", padx=10, pady=(0,6))

    def _sidebar_btn(self, text, cmd, parent):
        btn = tk.Button(parent, text=text, font=FONT_BTN,
                         bg=C["sidebar"], fg=C["text_primary"],
                         relief="flat", anchor="w", padx=10, pady=7,
                         activebackground=C["card_hover"],
                         activeforeground=C["text_primary"],
                         command=cmd)
        btn.pack(fill="x", pady=1)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=C["card_hover"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=C["sidebar"]))

    def _build_main(self):
        # هدر
        self.header = tk.Frame(self.main, bg=C["sidebar"], pady=10)
        self.header.pack(fill="x")

        self.hdr_title = tk.Label(self.header, text="همه اخبار",
                                   font=FONT_LARGE, fg=C["text_primary"],
                                   bg=C["sidebar"])
        self.hdr_title.pack(side="left", padx=14)

        self.hdr_count = tk.Label(self.header, text="", font=FONT_META,
                                   fg=C["text_secondary"], bg=C["sidebar"])
        self.hdr_count.pack(side="right", padx=14)

        # سوئیچ نمای telegram/reddit
        view_frame = tk.Frame(self.header, bg=C["sidebar"])
        view_frame.pack(side="right", padx=8)
        self._view_var = tk.StringVar(value=self._view_mode)
        for lbl, val in [("💬 تلگرام", "telegram"), ("📰 ردیت", "reddit")]:
            rb = tk.Radiobutton(view_frame, text=lbl, value=val,
                                 variable=self._view_var, font=FONT_BTN,
                                 fg=C["text_primary"], bg=C["sidebar"],
                                 selectcolor=C["accent"],
                                 activebackground=C["sidebar"],
                                 command=self._switch_view)
            rb.pack(side="left", padx=4)

        # فیلتر خوانده‌شده
        self.show_seen_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.header, text="نمایش خوانده‌شده",
                        variable=self.show_seen_var, font=FONT_BTN,
                        fg=C["text_secondary"], bg=C["sidebar"],
                        selectcolor=C["input_bg"],
                        activebackground=C["sidebar"],
                        command=self._reload_cards).pack(side="right", padx=6)

        # جستجو
        search_row = tk.Frame(self.main, bg=C["panel"], pady=5)
        search_row.pack(fill="x")
        tk.Label(search_row, text="🔎", fg=C["text_secondary"],
                  bg=C["panel"]).pack(side="left", padx=(12,4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._reload_cards())
        tk.Entry(search_row, textvariable=self.search_var, font=FONT_SUMMARY,
                  bg=C["input_bg"], fg=C["text_primary"], relief="flat",
                  insertbackground=C["text_primary"]).pack(
            side="left", fill="x", expand=True, padx=(0,12), ipady=4)

        # ناحیه محتوا
        self.content_area = tk.Frame(self.main, bg=C["bg"])
        self.content_area.pack(fill="both", expand=True)
        self._build_telegram_area()

        # نوار وضعیت پایین
        self.status_bar = tk.Frame(self.main, bg=C["sidebar"])
        self.status_bar.pack(fill="x", side="bottom")

        self.status_lbl = tk.Label(self.status_bar, text="آماده", font=FONT_META,
                                    fg=C["text_secondary"], bg=C["sidebar"],
                                    anchor="w")
        self.status_lbl.pack(side="left", padx=10, pady=4)

        # اینترنت در نوار پایین
        self.net_status_lbl = tk.Label(self.status_bar, text="🌐 بررسی...",
                                        font=FONT_META, fg=C["text_secondary"],
                                        bg=C["sidebar"], anchor="e")
        self.net_status_lbl.pack(side="right", padx=10, pady=4)

    def _build_telegram_area(self):
        for w in self.content_area.winfo_children():
            w.destroy()
        self._reddit_view = None

        self.canvas = tk.Canvas(self.content_area, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self.content_area, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.cards_frame = tk.Frame(self.canvas, bg=C["bg"])
        self._cw = self.canvas.create_window((0,0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._cw, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _build_reddit_area(self):
        for w in self.content_area.winfo_children():
            w.destroy()
        if not self._active_feed:
            tk.Label(self.content_area,
                      text="برای نمای ردیت ابتدا یک فید رو انتخاب کن.",
                      font=FONT_SUMMARY, fg=C["text_secondary"],
                      bg=C["bg"]).pack(pady=60)
            return
        self._reddit_view = RedditView(
            self.content_area, self._active_feed, self.store,
            on_open_item=self._open_item)
        self._reddit_view.pack(fill="both", expand=True)

    def _switch_view(self):
        self._view_mode = self._view_var.get()
        if self._view_mode == "telegram":
            self._build_telegram_area()
            self._reload_cards()
        else:
            self._build_reddit_area()

    # ---- فیدها در sidebar ----
    def _refresh_sidebar(self):
        for w in self._feed_inner.winfo_children():
            w.destroy()

        # دکمه "همه"
        self._feed_row("📰 همه اخبار", None, pinned=False)

        for f in self.store.get_feeds():
            from urllib.parse import urlparse
            domain = urlparse(f["url"]).netloc or f["url"][:28]
            prefix = "📌 " if f["pinned"] else "📄 "
            self._feed_row(prefix + domain, f["url"], pinned=f["pinned"])

    def _feed_row(self, text, url, pinned=False):
        is_active = (url == self._active_feed)
        bg = C["accent"] if is_active else C["sidebar"]

        row = tk.Frame(self._feed_inner, bg=bg)
        row.pack(fill="x")

        btn = tk.Button(row, text=text, font=FONT_BTN, bg=bg,
                         fg=C["text_primary"], relief="flat",
                         anchor="w", padx=10, pady=6,
                         command=lambda u=url: self._select_feed(u))
        btn.pack(side="left", fill="x", expand=True)
        btn.bind("<Enter>", lambda e, r=row, b=btn: (r.configure(bg=C["card_hover"]),
                                                      b.configure(bg=C["card_hover"])))
        btn.bind("<Leave>", lambda e, r=row, b=btn, bg=bg: (r.configure(bg=bg),
                                                              b.configure(bg=bg)))

        if url:
            # پین
            pin_text = "📌" if not pinned else "🔓"
            tk.Button(row, text=pin_text, font=("", 8),
                       bg=bg, fg=C["text_secondary"], relief="flat", padx=2,
                       command=lambda u=url, p=pinned: self._toggle_pin(u, p)
                       ).pack(side="right")
            # حذف
            tk.Button(row, text="✕", font=("", 8),
                       bg=bg, fg=C["danger"], relief="flat", padx=4,
                       command=lambda u=url: self._del_feed(u)
                       ).pack(side="right")

    def _select_feed(self, url):
        self._active_feed = url
        from urllib.parse import urlparse
        title = "همه اخبار" if url is None else urlparse(url).netloc
        self.hdr_title.configure(text=title)
        self._refresh_sidebar()
        if self._view_mode == "reddit":
            self._build_reddit_area()
        else:
            self._reload_cards()
        if url:
            self._set_status(f"در حال دریافت: {url}")
            threading.Thread(target=self._fetch_and_show, args=(url,), daemon=True).start()

    def _fetch_and_show(self, url):
        items = core.fetch_feed(url)
        for it in items:
            self.store.upsert(it, url)
        self.root.after(0, self._post_fetch, url, len(items))

    def _post_fetch(self, url, count):
        if self._view_mode == "reddit" and self._reddit_view:
            self._reddit_view.refresh()
        else:
            self._reload_cards()
        self._set_status(f"{count} خبر از {url}")

    # ---- کارت‌های تلگرام ----
    def _reload_cards(self):
        if self._view_mode == "reddit":
            return
        query = self.search_var.get().strip().lower()
        show_seen = self.show_seen_var.get()
        items = self.store.get_items(self._active_feed, sort=self._sort)
        if not show_seen:
            items = [i for i in items if not i.get("seen")]
        if query:
            items = [i for i in items if query in i.get("title","").lower()
                     or query in i.get("summary","").lower()]

        for w in self.cards_frame.winfo_children():
            w.destroy()
        self._cards = []

        if not items:
            tk.Label(self.cards_frame, text="خبری برای نمایش نیست.",
                      font=FONT_SUMMARY, fg=C["text_secondary"],
                      bg=C["bg"]).pack(pady=60)
        else:
            for item in items:
                card = NewsCard(self.cards_frame, item,
                                 on_click=self._open_item,
                                 on_image_loaded=self._on_img_loaded)
                card.pack(fill="x")
                self._cards.append(card)

        total = len(items)
        unseen = sum(1 for i in items if not i.get("seen"))
        self.hdr_count.configure(
            text=f"{unseen} نخوانده / {total}" if unseen else f"{total} خبر")

    def _open_item(self, item: dict):
        self.store.mark_seen(item["id"])
        item["seen"] = 1
        for card in self._cards:
            if card.item.get("id") == item["id"]:
                card.mark_seen()
                break
        NewsDetailWindow(self.root, item)
        unseen = sum(1 for c in self._cards if not c.item.get("seen"))
        self.hdr_count.configure(
            text=f"{unseen} نخوانده / {len(self._cards)}" if unseen else f"{len(self._cards)} خبر")

    def _on_img_loaded(self, item_id, url):
        if item_id and url:
            self.store.update_image(item_id, url)

    # ---- مدیریت فیدها ----
    def _add_feed(self):
        url = simpledialog.askstring("افزودن فید", "آدرس RSS را وارد کنید:", parent=self.root)
        if url and url.strip():
            url = url.strip()
            self.store.add_feed(url)
            self._refresh_sidebar()
            self._select_feed(url)

    def _del_feed(self, url):
        if messagebox.askyesno("حذف فید", f"فید زیر حذف شود؟\n{url}", parent=self.root):
            self.store.remove_feed(url)
            if self._active_feed == url:
                self._active_feed = None
            self._refresh_sidebar()
            self._reload_cards()

    def _toggle_pin(self, url, currently_pinned):
        self.store.pin_feed(url, not currently_pinned)
        self._refresh_sidebar()

    def _check_all(self):
        self._set_status("بررسی همه فیدها...")
        def worker():
            feeds = self.store.get_feeds()
            for f in feeds:
                items = core.fetch_feed(f["url"])
                for it in items:
                    self.store.upsert(it, f["url"])
                time.sleep(0.3)
            self.root.after(0, self._reload_cards)
            self.root.after(0, lambda: self._set_status("✅ همه فیدها بررسی شدند."))
        threading.Thread(target=worker, daemon=True).start()

    # ---- DNS ----
    def _open_dns_scanner(self):
        DNSScannerWindow(self.root, self._apply_dns, self.store)

    def _apply_dns(self, server: dict):
        config.ACTIVE_DOH = server
        core.install_doh_resolver(server["ip"], server["host"])
        lat = f" ({server['latency_ms']}ms)" if server.get("latency_ms") else ""
        self.dns_lbl.configure(text=f"DNS: {server['name']}{lat}")
        self._set_status(f"✅ DNS → {server['name']}")

    # ---- تم ----
    def _toggle_theme(self):
        new = "light" if self._theme_name == "dark" else "dark"
        self._apply_theme(new)

    # ---- لاگ ----
    def _open_log(self):
        LogWindow(self.root)

    # ---- وضعیت اینترنت ----
    def _on_internet_update(self, result: dict):
        self.root.after(0, self._update_net_ui, result)

    def _update_net_ui(self, result: dict):
        label = result.get("label", "نامشخص")
        color = result.get("color", C["text_secondary"])
        try:
            self.net_lbl.configure(text=label, fg=color)
            self.net_status_lbl.configure(text=f"🌐 {label}", fg=color)
        except Exception:
            pass

    # ---- وضعیت ----
    def _set_status(self, msg):
        try:
            self.status_lbl.configure(text=msg)
        except Exception:
            pass

    # ---- بارگذاری اولیه ----
    def _start_bg_threads(self):
        # اضافه کردن فیدهای پیش‌فرض اگه جدید هستن
        existing = {f["url"] for f in self.store.get_feeds()}
        for url in config.DEFAULT_FEEDS:
            if url not in existing:
                self.store.add_feed(url)
        self._refresh_sidebar()

        threading.Thread(target=self._initial_load, daemon=True).start()

        if config.CHECK_INTERVAL > 0:
            def auto():
                while True:
                    time.sleep(config.CHECK_INTERVAL)
                    for f in self.store.get_feeds():
                        items = core.fetch_feed(f["url"])
                        for it in items:
                            self.store.upsert(it, f["url"])
                    self.root.after(0, self._reload_cards)
            threading.Thread(target=auto, daemon=True).start()

    def _initial_load(self):
        self.root.after(0, lambda: self._set_status("در حال دریافت فیدها..."))
        for f in self.store.get_feeds():
            items = core.fetch_feed(f["url"])
            for it in items:
                self.store.upsert(it, f["url"])
        self.root.after(0, self._reload_cards)
        self.root.after(0, lambda: self._set_status("✅ آماده"))


# ---------------------------------------------------------------------------
# اجرا
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.tk.call("font", "configure", "TkDefaultFont", "-family", "Tahoma")
    except Exception:
        pass
    app = RSSApp(root)
    root.mainloop()
