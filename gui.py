"""
gui.py - RSS Reader UI
Telegram-style feed list + Reddit-style feed view + Settings + Video player
"""
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import threading
import time
import webbrowser
import io
import os

try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import vlc
    VLC_OK = True
except ImportError:
    VLC_OK = False

import core
import config
import i18n
from i18n import t

# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg":"#17212B","sidebar":"#0E1621","card":"#1E2C3A","card_seen":"#17212B",
        "card_hover":"#243447","accent":"#2196F3","accent2":"#64B5F6",
        "text_primary":"#FFFFFF","text_secondary":"#7B8EA0","text_seen":"#5B6C7D",
        "badge":"#2196F3","separator":"#0E1621","input_bg":"#242F3D",
        "btn":"#2196F3","btn_hover":"#1976D2","danger":"#E53935",
        "success":"#43A047","warning":"#FB8C00","panel":"#1C2A38",
        "reddit_header":"#1A2839","reddit_card":"#1E2C3A","reddit_border":"#2A3D52",
        "tag_bg":"#243447","tag_fg":"#64B5F6",
    },
    "light": {
        "bg":"#F6F7F8","sidebar":"#FFFFFF","card":"#FFFFFF","card_seen":"#F0F2F5",
        "card_hover":"#E8EDF2","accent":"#0079D3","accent2":"#1484D6",
        "text_primary":"#1C1C1C","text_secondary":"#7C7C7C","text_seen":"#AAAAAA",
        "badge":"#0079D3","separator":"#EDEFF1","input_bg":"#EDEFF1",
        "btn":"#0079D3","btn_hover":"#006BBD","danger":"#E53935",
        "success":"#43A047","warning":"#FB8C00","panel":"#EDEFF1",
        "reddit_header":"#FFFFFF","reddit_card":"#FFFFFF","reddit_border":"#EDEFF1",
        "tag_bg":"#E8F0FE","tag_fg":"#0079D3",
    },
}
C = THEMES["dark"]

# fonts — rebuilt when font_size changes
def _fonts(size=9):
    return {
        "title":   ("Segoe UI", size+1, "bold"),
        "body":    ("Segoe UI", size),
        "meta":    ("Segoe UI", size-1),
        "large":   ("Segoe UI", size+3, "bold"),
        "btn":     ("Segoe UI", size),
        "mono":    ("Courier New", size),
        "tag":     ("Segoe UI", size-1, "bold"),
    }
F = _fonts()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_placeholder(w=80, h=60):
    if not PIL_OK: return None
    img = Image.new("RGB", (w, h), C["card_hover"])
    draw = ImageDraw.Draw(img)
    draw.rectangle([w//4,h//4,3*w//4,3*h//4], outline=C["text_seen"], width=1)
    draw.line([w//4,h//4,3*w//4,3*h//4], fill=C["text_seen"], width=1)
    draw.line([3*w//4,h//4,w//4,3*h//4], fill=C["text_seen"], width=1)
    return ImageTk.PhotoImage(img)

def resize_image(data: bytes, w: int, h: int):
    if not PIL_OK or not data: return None
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        img.thumbnail((w, h), Image.LANCZOS)
        iw, ih = img.size
        img = img.crop(((iw-min(iw,w))//2, (ih-min(ih,h))//2,
                         (iw-min(iw,w))//2+min(iw,w), (ih-min(ih,h))//2+min(ih,h)))
        return ImageTk.PhotoImage(img)
    except: return None

def _btn(parent, text, cmd, bg=None, fg=None, **kw):
    b = tk.Button(parent, text=text, command=cmd,
                   bg=bg or C["btn"], fg=fg or "white",
                   font=F["btn"], relief="flat", padx=12, pady=6,
                   activebackground=C["btn_hover"],
                   activeforeground="white", **kw)
    return b

def _label(parent, text, font_key="body", fg_key="text_primary", **kw):
    return tk.Label(parent, text=text, font=F[font_key],
                     fg=C[fg_key], bg=C["bg"], **kw)

# ---------------------------------------------------------------------------
# Video Player Window
# ---------------------------------------------------------------------------
class VideoWindow(tk.Toplevel):
    def __init__(self, parent, video_url: str, video_type: str, title: str):
        super().__init__(parent)
        self.title(t("video_title"))
        self.geometry("800x520")
        self.configure(bg=C["bg"])
        self._url = video_url
        self._type = video_type
        self._player = None
        self._build(title)

    def _build(self, title):
        hdr = tk.Frame(self, bg=C["sidebar"], pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title[:80], font=F["btn"],
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=14)

        if self._type in ["direct", "redgifs"] and VLC_OK:
            self._build_vlc()
        elif self._type == "youtube":
            self._build_youtube()
        elif self._type == "redgifs":
            self._build_redgifs()
        else:
            self._build_fallback()

    def _build_vlc(self):
        frame = tk.Frame(self, bg="black")
        frame.pack(fill="both", expand=True)

        try:
            instance = vlc.Instance()
            self._player = instance.media_player_new()
            media = instance.media_new(self._url)
            self._player.set_media(media)
            # Enable audio
            self._player.audio_set_volume(100)  # Set volume to 100%
            # embed into tk frame
            self.update()
            if hasattr(self._player, "set_hwnd"):
                self._player.set_hwnd(frame.winfo_id())
            elif hasattr(self._player, "set_xwindow"):
                self._player.set_xwindow(frame.winfo_id())
            self._player.play()
        except Exception as e:
            core.LOG.error(f"VLC error: {e}")
            self._build_fallback()
            return

        ctrl = tk.Frame(self, bg=C["sidebar"], pady=8)
        ctrl.pack(fill="x")
        _btn(ctrl, "⏸ Pause/Play", self._toggle, bg=C["input_bg"],
              fg=C["text_primary"]).pack(side="left", padx=8)
        _btn(ctrl, "⏹ Stop", self._stop, bg=C["input_bg"],
              fg=C["text_primary"]).pack(side="left", padx=4)
        # Volume controls
        tk.Label(ctrl, text="🔈", font=F["meta"], bg=C["sidebar"],
                  fg=C["text_secondary"]).pack(side="left", padx=(12,4))
        _btn(ctrl, "−", lambda: self._volume(-10), bg=C["input_bg"],
              fg=C["text_primary"], padx=6, pady=2).pack(side="left", padx=2)
        _btn(ctrl, "＋", lambda: self._volume(10), bg=C["input_bg"],
              fg=C["text_primary"], padx=6, pady=2).pack(side="left", padx=2)
        _btn(ctrl, "🔗 Browser", lambda: webbrowser.open(self._url),
              bg=C["input_bg"], fg=C["text_primary"]).pack(side="right", padx=8)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_youtube(self):
        # embed YouTube in a simple HTML view via browser fallback
        vid_id = self._url.split("v=")[-1].split("&")[0]
        inner = tk.Frame(self, bg=C["bg"])
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="▶", font=("Segoe UI", 48),
                  fg=C["accent"], bg=C["bg"]).pack(pady=40)
        tk.Label(inner, text="YouTube video", font=F["large"],
                  fg=C["text_primary"], bg=C["bg"]).pack()
        tk.Label(inner, text=self._url, font=F["meta"],
                  fg=C["text_secondary"], bg=C["bg"]).pack(pady=8)
        _btn(inner, "🔗 Open in browser", lambda: webbrowser.open(self._url)
              ).pack(pady=12)

    def _build_redgifs(self):
        # Redgifs can be played directly via VLC, but we'll add a fallback UI
        inner = tk.Frame(self, bg=C["bg"])
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="🎬", font=("Segoe UI", 48),
                  fg=C["accent"], bg=C["bg"]).pack(pady=40)
        tk.Label(inner, text="Redgifs video", font=F["large"],
                  fg=C["text_primary"], bg=C["bg"]).pack()
        tk.Label(inner, text=self._url, font=F["meta"],
                  fg=C["text_secondary"], bg=C["bg"]).pack(pady=8)
        _btn(inner, "🔗 Open in browser", lambda: webbrowser.open(self._url)
              ).pack(pady=12)
        # Try to play with VLC anyway
        if VLC_OK:
            self.after(500, lambda: self._build_vlc() if self.winfo_exists() else None)

    def _build_fallback(self):
        tk.Label(self, text=t("video_no_vlc"), font=F["body"],
                  fg=C["warning"], bg=C["bg"]).pack(pady=20)
        webbrowser.open(self._url)
        self.after(2000, self.destroy)

    def _toggle(self):
        if self._player:
            if self._player.is_playing(): self._player.pause()
            else: self._player.play()

    def _stop(self):
        if self._player: self._player.stop()

    def _volume(self, delta):
        if self._player:
            current = self._player.audio_get_volume()
            new_vol = max(0, min(100, current + delta))
            self._player.audio_set_volume(new_vol)

    def _on_close(self):
        if self._player: self._player.stop()
        self.destroy()

# ---------------------------------------------------------------------------
# Detail Window (article)
# ---------------------------------------------------------------------------
class DetailWindow(tk.Toplevel):
    LONG_THRESHOLD = 300

    def __init__(self, parent, item: dict):
        super().__init__(parent)
        self.title(item.get("title","Article")[:60])
        self.geometry("740x580")
        self.configure(bg=C["bg"])
        self._item = item
        self._build()

    def _build(self):
        item = self._item
        summary = item.get("summary","")

        # Hero image
        self.hero = tk.Frame(self, bg=C["sidebar"], height=6)
        self.hero.pack(fill="x")
        if PIL_OK and item.get("image_url"):
            threading.Thread(target=self._load_hero, daemon=True).start()

        content = tk.Frame(self, bg=C["bg"])
        content.pack(fill="both", expand=True, padx=20, pady=16)

        # Title
        tk.Label(content, text=item.get("title",""), font=F["large"],
                  fg=C["text_primary"], bg=C["bg"],
                  wraplength=700, justify="left", anchor="w").pack(anchor="w")

        # Meta row
        meta_row = tk.Frame(content, bg=C["bg"])
        meta_row.pack(anchor="w", pady=(4,10))
        tk.Label(meta_row, text=f"📅 {item.get('published','')[:16]}",
                  font=F["meta"], fg=C["text_secondary"], bg=C["bg"]).pack(side="left")

        # Video button
        if item.get("video_url"):
            _btn(meta_row, t("play_video"),
                  lambda: VideoWindow(self, item["video_url"], item["video_type"],
                                       item.get("title","")),
                  bg=C["accent2"], fg=C["bg"]).pack(side="left", padx=10)

        tk.Frame(content, height=1, bg=C["separator"]).pack(fill="x", pady=(0,10))

        # Summary
        if len(summary) <= self.LONG_THRESHOLD:
            # Short — show inline
            tk.Label(content, text=summary or t("no_summary"),
                      font=F["body"], fg=C["text_primary"], bg=C["bg"],
                      wraplength=700, justify="left", anchor="w").pack(anchor="w")
        else:
            # Long — scrollable text widget
            txt = tk.Text(content, font=F["body"], fg=C["text_primary"],
                           bg=C["card"], relief="flat", wrap="word",
                           height=10, padx=12, pady=10)
            vsb = ttk.Scrollbar(content, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            txt.pack(side="left", fill="both", expand=True)
            vsb.pack(side="right", fill="y")
            txt.insert("1.0", summary)
            txt.config(state="disabled")

        # Buttons
        btn_row = tk.Frame(self, bg=C["bg"], pady=12)
        btn_row.pack(fill="x", padx=20)
        _btn(btn_row, t("open_browser"),
              lambda: webbrowser.open(item.get("link",""))).pack(side="left")
        _btn(btn_row, t("close"), self.destroy,
              bg=C["input_bg"], fg=C["text_primary"]).pack(side="right")

    def _load_hero(self):
        data = core.fetch_image_bytes(self._item["image_url"])
        if data:
            photo = resize_image(data, 720, 200)
            if photo:
                self.after(0, self._set_hero, photo)

    def _set_hero(self, photo):
        self.hero.configure(height=200)
        lbl = tk.Label(self.hero, image=photo, bg=C["sidebar"])
        lbl.image = photo
        lbl.pack(fill="both", expand=True)

# ---------------------------------------------------------------------------
# Settings Window
# ---------------------------------------------------------------------------
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, settings: dict, on_save):
        super().__init__(parent)
        self.title(t("settings_title"))
        self.geometry("520x560")
        self.configure(bg=C["bg"])
        self._s = dict(settings)
        self._on_save = on_save
        self._build()

    def _section(self, parent, label):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=20, pady=(14,2))
        tk.Label(f, text=label.upper(), font=F["meta"],
                  fg=C["accent2"], bg=C["bg"]).pack(anchor="w")
        tk.Frame(f, height=1, bg=C["accent"]).pack(fill="x", pady=(2,0))
        inner = tk.Frame(parent, bg=C["bg"])
        inner.pack(fill="x", padx=28, pady=4)
        return inner

    def _row(self, parent, label, widget_factory):
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, font=F["body"], fg=C["text_secondary"],
                  bg=C["bg"], width=28, anchor="w").pack(side="left")
        widget_factory(row)

    def _build(self):
        hdr = tk.Frame(self, bg=C["sidebar"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"⚙️  {t('settings_title')}", font=F["large"],
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=16)

        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        inner = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))

        # ── General ──
        g = self._section(inner, t("section_general"))

        self._lang_var = tk.StringVar(value=self._s.get("language","en"))
        self._row(g, t("lang_label"), lambda p: ttk.Combobox(
            p, textvariable=self._lang_var, values=["en","fa"],
            width=8, state="readonly").pack(side="left"))

        self._theme_var = tk.StringVar(value=self._s.get("theme","dark"))
        self._row(g, t("theme_label"), lambda p: ttk.Combobox(
            p, textvariable=self._theme_var,
            values=[t("theme_dark"), t("theme_light")],
            width=10, state="readonly").pack(side="left"))

        self._interval_var = tk.StringVar(value=str(self._s.get("check_interval",300)))
        self._row(g, t("interval_label"), lambda p: tk.Entry(
            p, textvariable=self._interval_var, width=8,
            bg=C["input_bg"], fg=C["text_primary"],
            relief="flat", font=F["mono"]).pack(side="left", ipady=3))

        # ── Feeds ──
        fd = self._section(inner, t("section_feeds"))

        self._sort_var = tk.StringVar(value=self._s.get("sort","newest"))
        self._row(fd, t("sort_label"), lambda p: ttk.Combobox(
            p, textvariable=self._sort_var,
            values=[t("sort_newest"), t("sort_oldest")],
            width=14, state="readonly").pack(side="left"))

        self._show_read_var = tk.BooleanVar(value=self._s.get("show_read", True))
        self._row(fd, t("show_read_label"), lambda p: tk.Checkbutton(
            p, variable=self._show_read_var,
            bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))

        # ── Display ──
        dp = self._section(inner, t("section_display"))

        self._font_var = tk.StringVar(value=str(self._s.get("font_size",9)))
        self._row(dp, t("font_size_label"), lambda p: ttk.Combobox(
            p, textvariable=self._font_var,
            values=["8","9","10","11","12"],
            width=6, state="readonly").pack(side="left"))

        self._card_var = tk.StringVar(value=self._s.get("card_style","telegram"))
        self._row(dp, t("card_style_label"), lambda p: ttk.Combobox(
            p, textvariable=self._card_var,
            values=["telegram","reddit"],
            width=10, state="readonly").pack(side="left"))

        self._img_var = tk.BooleanVar(value=self._s.get("load_images", True))
        self._row(dp, t("img_load_label"), lambda p: tk.Checkbutton(
            p, variable=self._img_var,
            bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))

        # ── Video ──
        vd = self._section(inner, t("section_video"))

        self._vid_int_var = tk.BooleanVar(value=self._s.get("video_internal", True))
        self._row(vd, t("video_internal"), lambda p: tk.Checkbutton(
            p, variable=self._vid_int_var,
            bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))

        # ── DNS ──
        dn = self._section(inner, t("section_dns"))
        self._dns_auto_var = tk.BooleanVar(value=self._s.get("dns_auto", False))
        self._row(dn, t("dns_auto_label"), lambda p: tk.Checkbutton(
            p, variable=self._dns_auto_var,
            bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))

        # Buttons
        btn_row = tk.Frame(self, bg=C["bg"], pady=14)
        btn_row.pack(fill="x", padx=20)
        _btn(btn_row, t("save"), self._save).pack(side="left")
        _btn(btn_row, t("cancel"), self.destroy,
              bg=C["input_bg"], fg=C["text_primary"]).pack(side="right")

    def _save(self):
        theme_map = {t("theme_dark"): "dark", t("theme_light"): "light",
                     "dark": "dark", "light": "light"}
        sort_map  = {t("sort_newest"): "newest", t("sort_oldest"): "oldest",
                     "newest": "newest", "oldest": "oldest"}
        self._s.update({
            "language":       self._lang_var.get(),
            "theme":          theme_map.get(self._theme_var.get(), "dark"),
            "check_interval": int(self._interval_var.get() or 300),
            "sort":           sort_map.get(self._sort_var.get(), "newest"),
            "show_read":      self._show_read_var.get(),
            "load_images":    self._img_var.get(),
            "font_size":      int(self._font_var.get() or 9),
            "card_style":     self._card_var.get(),
            "video_internal": self._vid_int_var.get(),
            "dns_auto":       self._dns_auto_var.get(),
        })
        self._on_save(self._s)
        self.destroy()

# ---------------------------------------------------------------------------
# DNS Scanner Window
# ---------------------------------------------------------------------------
class DNSScannerWindow(tk.Toplevel):
    def __init__(self, parent, on_select_cb):
        super().__init__(parent)
        self.title(t("dns_win_title"))
        self.geometry("800x620")
        self.configure(bg=C["bg"])
        self.on_select_cb = on_select_cb
        self._results = []
        self._build()
        self.after(200, self._start_scan)

    def _build(self):
        hdr = tk.Frame(self, bg=C["sidebar"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"🔍  {t('dns_win_title')}", font=F["large"],
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=16)
        self._prog_var = tk.StringVar(value=t("scanning"))
        tk.Label(hdr, textvariable=self._prog_var, font=F["body"],
                  fg=C["text_secondary"], bg=C["sidebar"]).pack(side="right", padx=16)

        # Custom DNS + file load
        add_row = tk.Frame(self, bg=C["panel"], pady=6)
        add_row.pack(fill="x", padx=8, pady=(8,0))

        self._cn = tk.Entry(add_row, width=9, font=F["mono"], bg=C["input_bg"],
                             fg=C["text_primary"], relief="flat",
                             insertbackground=C["text_primary"])
        self._cn.insert(0, t("custom_name"))
        self._cn.pack(side="left", padx=4, ipady=3)

        self._ci = tk.Entry(add_row, width=14, font=F["mono"], bg=C["input_bg"],
                             fg=C["text_primary"], relief="flat",
                             insertbackground=C["text_primary"])
        self._ci.insert(0, t("custom_ip"))
        self._ci.pack(side="left", padx=4, ipady=3)

        self._ch = tk.Entry(add_row, width=22, font=F["mono"], bg=C["input_bg"],
                             fg=C["text_primary"], relief="flat",
                             insertbackground=C["text_primary"])
        self._ch.insert(0, t("custom_host"))
        self._ch.pack(side="left", padx=4, ipady=3)

        _btn(add_row, t("add_custom_dns"), self._add_custom,
              bg=C["btn"], fg="white").pack(side="left", padx=6)
        _btn(add_row, t("load_file"), self._load_file,
              bg=C["input_bg"], fg=C["text_primary"]).pack(side="left", padx=4)

        self.pb = ttk.Progressbar(self, mode="indeterminate")
        self.pb.pack(fill="x", padx=8, pady=4)
        self.pb.start(12)

        cols = ("name","ip","latency","ok") + \
               tuple(s.replace("www.","").split(".")[0] for s in config.FILTER_TEST_SITES)
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self._style_tree()
        for col, hd, w in [("name","Server",120),("ip","IP",115),
                             ("latency","Latency",70),("ok","Status",60)]:
            self.tree.heading(col, text=hd)
            self.tree.column(col, width=w, anchor="center" if col!="name" else "w")
        for s in config.FILTER_TEST_SITES:
            col = s.replace("www.","").split(".")[0]
            self.tree.heading(col, text=col)
            self.tree.column(col, width=58, anchor="center")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8,0), pady=4)
        vsb.pack(side="left", fill="y", pady=4)

        bf = tk.Frame(self, bg=C["bg"], pady=8)
        bf.pack(fill="x", padx=8)
        self._use_btn = _btn(bf, t("use_dns"), self._use_selected, bg=C["btn"])
        self._use_btn.config(state="disabled")
        self._use_btn.pack(side="left", padx=4)
        _btn(bf, t("rescan"), self._start_scan,
              bg=C["input_bg"], fg=C["text_primary"]).pack(side="left", padx=4)
        _btn(bf, t("best_auto"), self._use_best,
              bg=C["accent2"], fg=C["bg"]).pack(side="right", padx=4)
        self.tree.bind("<<TreeviewSelect>>",
                        lambda e: self._use_btn.config(state="normal"))

    def _style_tree(self):
        s = ttk.Style(); s.theme_use("clam")
        s.configure("Treeview", background=C["card"], foreground=C["text_primary"],
                     fieldbackground=C["card"], rowheight=28, font=F["body"])
        s.configure("Treeview.Heading", background=C["sidebar"],
                     foreground=C["text_secondary"], font=F["btn"])
        s.map("Treeview", background=[("selected", C["accent"])])

    def _add_custom(self):
        name = self._cn.get().strip()
        ip   = self._ci.get().strip()
        host = self._ch.get().strip()
        if not name or not ip or ip == t("custom_ip"):
            messagebox.showwarning("Error", t("dns_err_fields"), parent=self)
            return
        srv = {"name": name, "ip": ip, "host": host or ip}
        if srv not in config.DOH_SERVERS:
            config.DOH_SERVERS.append(srv)
        core.LOG.info(f"Custom DNS added: {name} ({ip})")
        self._start_scan()

    def _load_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Load DNS list",
            filetypes=[("Text files","*.txt"),("All files","*.*")])
        if not path: return
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                ips = [line.strip() for line in f if line.strip() and
                        not line.startswith("#")]
            added = 0
            for ip in ips:
                # validate basic IP format
                parts = ip.split(".")
                if len(parts) == 4 and all(p.isdigit() and 0<=int(p)<=255 for p in parts):
                    srv = {"name": f"Custom ({ip})", "ip": ip, "host": ip}
                    if srv not in config.DOH_SERVERS:
                        config.DOH_SERVERS.append(srv)
                        added += 1
            core.LOG.info(f"Loaded {added} DNS IPs from {os.path.basename(path)}")
            self._start_scan()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _start_scan(self):
        self.tree.delete(*self.tree.get_children())
        self._results = []
        self.pb.start(12)
        self._prog_var.set(t("scanning"))

        def scan():
            scanner = core.DNSScanner()
            results = scanner.scan_all(
                config.DOH_SERVERS, config.FILTER_TEST_SITES,
                progress_cb=lambda r: self.after(0, self._add_row, r))
            self._results = results
            self.after(0, self._done, results)
        threading.Thread(target=scan, daemon=True).start()

    def _add_row(self, r):
        lat = f"{r['latency_ms']}ms" if r["latency_ms"] else "—"
        ok  = "✅" if r["working"] else "❌"
        fv  = []
        for s in config.FILTER_TEST_SITES:
            v = r["filters"].get(s)
            fv.append("?" if v is None else ("🔴" if v else "🟢"))
        row = (r["name"], r["ip"], lat, ok) + tuple(fv)
        try:
            self.tree.insert("", "end", iid=r["ip"], values=row,
                              tags=("ok" if r["working"] else "dead",))
            self.tree.tag_configure("ok",   foreground=C["text_primary"])
            self.tree.tag_configure("dead", foreground=C["text_seen"])
        except: pass

    def _done(self, results):
        self.pb.stop()
        ok = sum(1 for r in results if r["working"])
        self._prog_var.set(t("scan_done", ok=ok, total=len(results)))

    def _use_selected(self):
        sel = self.tree.selection()
        if not sel: return
        srv = next((r for r in self._results if r["ip"] == sel[0]), None)
        if srv: self.on_select_cb(srv); self.destroy()

    def _use_best(self):
        if not self._results:
            messagebox.showwarning("Wait", t("scan_wait"), parent=self); return
        best = core.DNSScanner().best_server(self._results)
        if best: self.on_select_cb(best); self.destroy()
        else: messagebox.showerror("Error", t("no_server"), parent=self)

# ---------------------------------------------------------------------------
# Log Window
# ---------------------------------------------------------------------------
class LogWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title(t("log_title"))
        self.geometry("760x460")
        self.configure(bg=C["bg"])
        self._build()
        for line in core.LOG.get_lines(): self._append(line)
        core.LOG.add_callback(self._append)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        hdr = tk.Frame(self, bg=C["sidebar"], pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"📋 {t('log_title')}", font=F["large"],
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=14)
        _btn(hdr, t("log_clear"), self._clear,
              bg=C["input_bg"], fg=C["text_primary"]).pack(side="right", padx=10)
        self.txt = tk.Text(self, font=F["mono"], bg=C["card"],
                            fg=C["text_primary"], relief="flat",
                            wrap="none", state="disabled", padx=8, pady=6)
        vsb = ttk.Scrollbar(self, orient="vertical",  command=self.txt.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.txt.tag_configure("ERROR", foreground=C["danger"])
        self.txt.tag_configure("WARN ", foreground=C["warning"])
        self.txt.tag_configure("DEBUG", foreground=C["text_seen"])
        self.txt.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")

    def _append(self, line):
        self.txt.config(state="normal")
        tag = next((lvl for lvl in ("ERROR","WARN ","DEBUG") if lvl in line), "INFO ")
        self.txt.insert("end", line+"\n", tag)
        self.txt.see("end")
        self.txt.config(state="disabled")

    def _clear(self):
        self.txt.config(state="normal"); self.txt.delete("1.0","end")
        self.txt.config(state="disabled")

    def _close(self):
        core.LOG.remove_callback(self._append); self.destroy()

# ---------------------------------------------------------------------------
# News Card (Telegram style)
# ---------------------------------------------------------------------------
class NewsCard(tk.Frame):
    TW, TH = 80, 60

    def __init__(self, master, item, on_click, load_images=True, **kw):
        seen = bool(item.get("seen"))
        bg = C["card_seen"] if seen else C["card"]
        super().__init__(master, bg=bg, cursor="hand2", **kw)
        self.item = item
        self.on_click = on_click
        self._bg = bg
        self._photo = None
        self._load_images = load_images
        self._ph = make_placeholder(self.TW, self.TH)
        self._build()
        self._bind_all()
        if load_images: self._load_img_async()

    def _build(self):
        seen = bool(self.item.get("seen"))
        tc = C["text_seen"] if seen else C["text_primary"]
        mc = C["text_seen"] if seen else C["text_secondary"]

        self.img_lbl = tk.Label(self, bg=self._bg, image=self._ph,
                                 width=self.TW, height=self.TH)
        self.img_lbl.image = self._ph
        self.img_lbl.pack(side="left", padx=(10,8), pady=8)

        tf = tk.Frame(self, bg=self._bg)
        tf.pack(side="left", fill="both", expand=True, pady=8, padx=(0,8))

        # Video badge
        if self.item.get("video_url"):
            tk.Label(tf, text="▶ VIDEO", font=F["tag"],
                      fg=C["accent2"], bg=self._bg).pack(anchor="w")

        tk.Label(tf, text=self.item.get("title",""), font=F["title"],
                  fg=tc, bg=self._bg, anchor="w", justify="left",
                  wraplength=400).pack(anchor="w")

        sm = self.item.get("summary","")
        if sm:
            tk.Label(tf, text=sm[:100]+("…" if len(sm)>100 else ""),
                      font=F["body"], fg=mc, bg=self._bg,
                      anchor="w", justify="left", wraplength=400).pack(anchor="w", pady=(2,0))

        from urllib.parse import urlparse as up
        domain = up(self.item.get("feed","")).netloc
        pub = self.item.get("published","")[:16]
        meta = f"{pub}  •  {domain}" if domain else pub
        tk.Label(tf, text=meta, font=F["meta"], fg=mc,
                  bg=self._bg, anchor="w").pack(anchor="w", pady=(3,0))

        if not seen:
            tk.Label(self, text="●", fg=C["badge"], bg=self._bg,
                      font=("",8)).pack(side="right", padx=8)

        tk.Frame(self, height=1, bg=C["separator"]).pack(side="bottom", fill="x")
        for w in tf.winfo_children(): self._bw(w)

    def _bw(self, w):
        w.bind("<Button-1>", self._clicked)
        w.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        w.bind("<Leave>",    lambda e: self._sbg(self._bg))

    def _bind_all(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        self.bind("<Leave>",    lambda e: self._sbg(self._bg))
        for w in self.winfo_children(): self._bw(w)

    def _sbg(self, color):
        self.configure(bg=color)
        for w in self.winfo_children():
            try: w.configure(bg=color)
            except: pass

    def _clicked(self, e=None): self.on_click(self.item)

    def _load_img_async(self):
        def worker():
            url = self.item.get("image_url","")
            data = core.fetch_image_bytes(url) if url else b""
            if not data and self.item.get("link"):
                og = core.fetch_og_image(self.item["link"])
                if og:
                    self.item["image_url"] = og
                    data = core.fetch_image_bytes(og)
            if data:
                photo = resize_image(data, self.TW, self.TH)
                if photo: self.after(0, self._si, photo)
        threading.Thread(target=worker, daemon=True).start()

    def _si(self, photo):
        self._photo = photo
        try: self.img_lbl.configure(image=photo); self.img_lbl.image = photo
        except: pass

    def mark_seen(self):
        self._bg = C["card_seen"]; self._sbg(self._bg); self.item["seen"] = 1
        for w in self.winfo_children():
            if isinstance(w, tk.Label) and w.cget("text") == "●": w.destroy()

# ---------------------------------------------------------------------------
# Reddit Card
# ---------------------------------------------------------------------------
class RedditCard(tk.Frame):
    IW, IH = 160, 100

    def __init__(self, master, item, index, on_click, load_images=True, **kw):
        bg = C["reddit_card"]
        super().__init__(master, bg=bg, cursor="hand2", **kw)
        self.item = item
        self.on_click = on_click
        self._bg = bg
        self._photo = None
        self._load_images = load_images
        self._build(index)
        self._bind_all()
        if load_images: self._load_img_async()

    def _build(self, idx):
        seen = bool(self.item.get("seen"))
        tc = C["text_seen"] if seen else C["text_primary"]
        mc = C["text_secondary"]

        # index
        tk.Label(self, text=f"{idx}.", font=F["meta"],
                  fg=C["text_secondary"], bg=self._bg,
                  width=3, anchor="n").pack(side="left", padx=(8,2), pady=12, anchor="n")

        # image
        ph = make_placeholder(self.IW, self.IH)
        self.img_lbl = tk.Label(self, bg=self._bg, image=ph,
                                 width=self.IW, height=self.IH)
        self.img_lbl.image = ph
        self.img_lbl.pack(side="left", padx=(4,12), pady=10, anchor="n")

        tf = tk.Frame(self, bg=self._bg)
        tf.pack(side="left", fill="both", expand=True, pady=10, padx=(0,12))

        # tags row
        tag_row = tk.Frame(tf, bg=self._bg)
        tag_row.pack(anchor="w", pady=(0,3))
        from urllib.parse import urlparse as up
        domain = up(self.item.get("feed","")).netloc
        if domain:
            tk.Label(tag_row, text=domain, font=F["tag"],
                      fg=C["tag_fg"], bg=C["tag_bg"],
                      padx=5, pady=1).pack(side="left", padx=(0,4))
        if self.item.get("video_url"):
            tk.Label(tag_row, text="VIDEO", font=F["tag"],
                      fg="white", bg=C["accent"],
                      padx=5, pady=1).pack(side="left", padx=2)

        # title
        tk.Label(tf, text=self.item.get("title",""), font=F["title"],
                  fg=tc, bg=self._bg, anchor="w", justify="left",
                  wraplength=480).pack(anchor="w")

        # summary — short inline, long truncated
        sm = self.item.get("summary","")
        if sm:
            display = sm if len(sm) <= 300 else sm[:200] + "…  [click to read more]"
            tk.Label(tf, text=display, font=F["body"], fg=mc,
                      bg=self._bg, anchor="w", justify="left",
                      wraplength=480).pack(anchor="w", pady=(4,0))

        pub = self.item.get("published","")[:16]
        tk.Label(tf, text=f"📅 {pub}", font=F["meta"],
                  fg=C["text_secondary"], bg=self._bg, anchor="w").pack(anchor="w", pady=(6,0))

        tk.Frame(self, height=1, bg=C["reddit_border"]).pack(side="bottom", fill="x")
        for w in tf.winfo_children(): self._bw(w)
        for w in tag_row.winfo_children(): self._bw(w)

    def _bw(self, w):
        w.bind("<Button-1>", self._clicked)
        w.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        w.bind("<Leave>",    lambda e: self._sbg(self._bg))

    def _bind_all(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        self.bind("<Leave>",    lambda e: self._sbg(self._bg))
        for w in self.winfo_children(): self._bw(w)

    def _sbg(self, color):
        self.configure(bg=color)
        for w in self.winfo_children():
            try: w.configure(bg=color)
            except: pass

    def _clicked(self, e=None): self.on_click(self.item)

    def _load_img_async(self):
        def worker():
            url = self.item.get("image_url","")
            data = core.fetch_image_bytes(url) if url else b""
            if not data and self.item.get("link"):
                og = core.fetch_og_image(self.item["link"])
                if og:
                    self.item["image_url"] = og
                    data = core.fetch_image_bytes(og)
            if data:
                photo = resize_image(data, self.IW, self.IH)
                if photo: self.after(0, self._si, photo)
        threading.Thread(target=worker, daemon=True).start()

    def _si(self, photo):
        self._photo = photo
        try: self.img_lbl.configure(image=photo); self.img_lbl.image = photo
        except: pass

# ---------------------------------------------------------------------------
# Scrollable card container
# ---------------------------------------------------------------------------
class ScrollableFrame(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.inner = tk.Frame(self.canvas, bg=C["bg"])
        self._win = self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(
            self._win, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)),"units"))

# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
class RSSApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self._settings = config.load_settings()
        self._apply_settings_globals(rebuild=False)

        self.store = core.Store(config.DB_FILE)
        self._active_feed = None
        self._view_mode   = self._settings.get("card_style","telegram")
        self._cards       = []
        self._sf          = None   # ScrollableFrame

        doh = config.ACTIVE_DOH
        core.install_doh_resolver(doh["ip"], doh["host"])

        self._monitor = core.InternetMonitor(interval=60,
                                               on_update=self._on_net_update)
        self._apply_ttk_style()
        self._build()
        self._refresh_sidebar()
        self._monitor.start()
        self._start_bg()

    # ── Settings ──
    def _apply_settings_globals(self, rebuild=True):
        global C, F
        s = self._settings
        i18n.set_lang(s.get("language","en"))
        C = THEMES[s.get("theme","dark")]
        F = _fonts(s.get("font_size",9))
        self._view_mode = s.get("card_style","telegram")
        config.CHECK_INTERVAL = s.get("check_interval", 300)
        if rebuild: self._full_rebuild()

    def _full_rebuild(self):
        for w in self.root.winfo_children(): w.destroy()
        self.root.configure(bg=C["bg"])
        self._cards = []
        self._sf    = None
        self._apply_ttk_style()
        self._build()
        self._refresh_sidebar()

    def _apply_ttk_style(self):
        s = ttk.Style(); s.theme_use("clam")
        s.configure("TScrollbar", background=C["sidebar"],
                     troughcolor=C["bg"], arrowcolor=C["text_secondary"])

    # ── Layout ──
    def _build(self):
        self.root.title(t("app_title"))

        self.sidebar = tk.Frame(self.root, bg=C["sidebar"], width=235)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        self.main = tk.Frame(self.root, bg=C["bg"])
        self.main.pack(side="left", fill="both", expand=True)
        self._build_main()

    def _build_sidebar(self):
        # Logo + theme toggle
        logo = tk.Frame(self.sidebar, bg=C["sidebar"], pady=14)
        logo.pack(fill="x")
        tk.Label(logo, text="📡 "+t("app_title"), font=F["large"],
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=12)
        tk.Button(logo, text="☀️" if self._settings.get("theme")=="dark" else "🌙",
                   font=("",11), bg=C["sidebar"], fg=C["text_primary"],
                   relief="flat", command=self._toggle_theme
                   ).pack(side="right", padx=8)

        tk.Frame(self.sidebar, height=1, bg=C["bg"]).pack(fill="x")

        tools = tk.Frame(self.sidebar, bg=C["sidebar"], pady=4)
        tools.pack(fill="x", padx=6)
        for label_key, cmd in [
            ("dns_scanner",  self._open_dns),
            ("add_feed",     self._add_feed),
            ("check_all",    self._check_all),
            ("log",          self._open_log),
            ("settings",     self._open_settings),
        ]:
            self._sb_btn(tools, t(label_key), cmd)

        tk.Frame(self.sidebar, height=1, bg=C["bg"]).pack(fill="x", pady=4)
        tk.Label(self.sidebar, text=t("feeds"), font=F["meta"],
                  fg=C["text_secondary"], bg=C["sidebar"]).pack(anchor="w", padx=14, pady=(2,2))

        # Feed list
        wrap = tk.Frame(self.sidebar, bg=C["sidebar"])
        wrap.pack(fill="both", expand=True)
        cv = tk.Canvas(wrap, bg=C["sidebar"], highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        cv.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._feed_inner = tk.Frame(cv, bg=C["sidebar"])
        cw = cv.create_window((0,0), window=self._feed_inner, anchor="nw")
        self._feed_inner.bind("<Configure>", lambda e: cv.configure(
            scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(cw, width=e.width))

        # Bottom status
        bot = tk.Frame(self.sidebar, bg=C["sidebar"])
        bot.pack(side="bottom", fill="x")
        self._dns_lbl = tk.Label(bot, text=f"DNS: {config.ACTIVE_DOH['name']}",
                                  font=F["meta"], fg=C["text_secondary"], bg=C["sidebar"])
        self._dns_lbl.pack(anchor="w", padx=10, pady=(4,0))
        self._net_side_lbl = tk.Label(bot, text=t("net_checking"),
                                       font=F["meta"], fg=C["text_secondary"],
                                       bg=C["sidebar"])
        self._net_side_lbl.pack(anchor="w", padx=10, pady=(0,6))

    def _sb_btn(self, parent, text, cmd):
        icon_map = {"DNS Scanner":"🔍 ","Add Feed":"➕ ","Refresh All":"🔄 ",
                    "App Log":"📋 ","Settings":"⚙️ ",
                    "اسکنر DNS":"🔍 ","افزودن فید":"➕ ","چک همه":"🔄 ",
                    "لاگ برنامه":"📋 ","تنظیمات":"⚙️ "}
        display = icon_map.get(text, "") + text
        btn = tk.Button(parent, text=display, font=F["btn"],
                         bg=C["sidebar"], fg=C["text_primary"],
                         relief="flat", anchor="w", padx=10, pady=7,
                         activebackground=C["card_hover"],
                         activeforeground=C["text_primary"], command=cmd)
        btn.pack(fill="x", pady=1)
        btn.bind("<Enter>", lambda e,b=btn: b.configure(bg=C["card_hover"]))
        btn.bind("<Leave>", lambda e,b=btn: b.configure(bg=C["sidebar"]))

    def _build_main(self):
        # Header
        self._hdr = tk.Frame(self.main, bg=C["sidebar"], pady=10)
        self._hdr.pack(fill="x")
        self._hdr_title = tk.Label(self._hdr, text=t("all_news"),
                                    font=F["large"], fg=C["text_primary"],
                                    bg=C["sidebar"])
        self._hdr_title.pack(side="left", padx=14)
        self._hdr_count = tk.Label(self._hdr, text="", font=F["meta"],
                                    fg=C["text_secondary"], bg=C["sidebar"])
        self._hdr_count.pack(side="right", padx=14)

        # View toggle
        vf = tk.Frame(self._hdr, bg=C["sidebar"])
        vf.pack(side="right", padx=6)
        self._view_var = tk.StringVar(value=self._view_mode)
        for lbl, val in [(t("view_telegram"),"telegram"),(t("view_reddit"),"reddit")]:
            tk.Radiobutton(vf, text=lbl, value=val, variable=self._view_var,
                            font=F["btn"], fg=C["text_primary"], bg=C["sidebar"],
                            selectcolor=C["accent"],
                            activebackground=C["sidebar"],
                            command=self._switch_view).pack(side="left", padx=4)

        # Show read
        self._show_read_var = tk.BooleanVar(value=self._settings.get("show_read",True))
        tk.Checkbutton(self._hdr, text=t("show_read"),
                        variable=self._show_read_var, font=F["btn"],
                        fg=C["text_secondary"], bg=C["sidebar"],
                        selectcolor=C["input_bg"],
                        activebackground=C["sidebar"],
                        command=self._reload).pack(side="right", padx=6)

        # Sort
        self._sort_var = tk.StringVar(value=self._settings.get("sort","newest"))
        sf = tk.Frame(self._hdr, bg=C["sidebar"])
        sf.pack(side="right", padx=4)
        for lbl, val in [(t("sort_newest"),"newest"),(t("sort_oldest"),"oldest")]:
            tk.Radiobutton(sf, text=lbl, value=val, variable=self._sort_var,
                            font=F["meta"], fg=C["text_secondary"], bg=C["sidebar"],
                            selectcolor=C["accent"],
                            activebackground=C["sidebar"],
                            command=self._reload).pack(side="left", padx=2)

        # Search
        sr = tk.Frame(self.main, bg=C["panel"], pady=5)
        sr.pack(fill="x")
        tk.Label(sr, text="🔎", fg=C["text_secondary"], bg=C["panel"],
                  font=F["body"]).pack(side="left", padx=(12,4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._reload())
        tk.Entry(sr, textvariable=self._search_var, font=F["body"],
                  bg=C["input_bg"], fg=C["text_primary"], relief="flat",
                  insertbackground=C["text_primary"]).pack(
            side="left", fill="x", expand=True, padx=(0,12), ipady=4)

        # Content
        self._content = tk.Frame(self.main, bg=C["bg"])
        self._content.pack(fill="both", expand=True)
        self._build_content_area()

        # Status bar
        sb = tk.Frame(self.main, bg=C["sidebar"])
        sb.pack(fill="x", side="bottom")
        self._status_lbl = tk.Label(sb, text=t("ready"), font=F["meta"],
                                     fg=C["text_secondary"], bg=C["sidebar"], anchor="w")
        self._status_lbl.pack(side="left", padx=10, pady=4)
        self._net_lbl = tk.Label(sb, text="🌐 ...", font=F["meta"],
                                  fg=C["text_secondary"], bg=C["sidebar"], anchor="e")
        self._net_lbl.pack(side="right", padx=10, pady=4)

    def _build_content_area(self):
        for w in self._content.winfo_children(): w.destroy()
        self._sf = ScrollableFrame(self._content, bg=C["bg"])
        self._sf.pack(fill="both", expand=True)

    # ── Sidebar feed list ──
    def _refresh_sidebar(self):
        for w in self._feed_inner.winfo_children(): w.destroy()
        self._feed_row(t("all_feeds"), None)
        for f in self.store.get_feeds():
            from urllib.parse import urlparse as up
            domain = up(f["url"]).netloc or f["url"][:26]
            prefix = "📌 " if f["pinned"] else "  "
            self._feed_row(prefix + domain, f["url"], f["pinned"])

    def _feed_row(self, text, url, pinned=False):
        is_active = url == self._active_feed
        bg = C["accent"] if is_active else C["sidebar"]
        row = tk.Frame(self._feed_inner, bg=bg)
        row.pack(fill="x")
        btn = tk.Button(row, text=text, font=F["btn"], bg=bg,
                         fg=C["text_primary"], relief="flat",
                         anchor="w", padx=10, pady=6,
                         command=lambda u=url: self._select_feed(u))
        btn.pack(side="left", fill="x", expand=True)
        btn.bind("<Enter>", lambda e,r=row,b=btn: (r.configure(bg=C["card_hover"]),
                                                    b.configure(bg=C["card_hover"])))
        btn.bind("<Leave>", lambda e,r=row,b=btn,bg=bg: (r.configure(bg=bg),
                                                           b.configure(bg=bg)))
        if url:
            pt = "🔓" if pinned else "📌"
            tk.Button(row, text=pt, font=("",8), bg=bg,
                       fg=C["text_secondary"], relief="flat", padx=2,
                       command=lambda u=url,p=pinned: self._toggle_pin(u,p)
                       ).pack(side="right")
            tk.Button(row, text="✕", font=("",8), bg=bg,
                       fg=C["danger"], relief="flat", padx=4,
                       command=lambda u=url: self._del_feed(u)
                       ).pack(side="right")

    def _select_feed(self, url):
        self._active_feed = url
        from urllib.parse import urlparse as up
        title = t("all_news") if url is None else up(url).netloc
        self._hdr_title.configure(text=title)
        self._refresh_sidebar()
        self._reload()
        if url:
            self._set_status(t("fetching", url=url))
            threading.Thread(target=self._fetch_feed, args=(url,), daemon=True).start()

    # ── Cards ──
    def _reload(self):
        if not hasattr(self, "_sf") or self._sf is None: return
        q     = self._search_var.get().strip().lower() if hasattr(self,"_search_var") else ""
        show  = self._show_read_var.get() if hasattr(self,"_show_read_var") else True
        sort  = self._sort_var.get() if hasattr(self,"_sort_var") else "newest"
        mode  = self._view_var.get() if hasattr(self,"_view_var") else "telegram"
        load_img = self._settings.get("load_images", True)

        items = self.store.get_items(self._active_feed, sort=sort)
        if not show: items = [i for i in items if not i.get("seen")]
        if q:        items = [i for i in items if q in i.get("title","").lower()
                               or q in i.get("summary","").lower()]

        for w in self._sf.inner.winfo_children(): w.destroy()
        self._cards = []

        if not items:
            tk.Label(self._sf.inner, text=t("no_articles"), font=F["body"],
                      fg=C["text_secondary"], bg=C["bg"]).pack(pady=60)
        elif mode == "reddit":
            for i, item in enumerate(items, 1):
                card = RedditCard(self._sf.inner, item, i,
                                   on_click=self._open_item,
                                   load_images=load_img)
                card.pack(fill="x", padx=4, pady=2)
                self._cards.append(card)
        else:
            for item in items:
                card = NewsCard(self._sf.inner, item,
                                 on_click=self._open_item,
                                 load_images=load_img)
                card.pack(fill="x")
                self._cards.append(card)

        total  = len(items)
        unseen = sum(1 for i in items if not i.get("seen"))
        self._hdr_count.configure(
            text=t("unread_of", unread=unseen, total=total) if unseen
            else t("n_articles", n=total))

    def _open_item(self, item):
        self.store.mark_seen(item["id"]); item["seen"] = 1
        for c in self._cards:
            if hasattr(c,"item") and c.item.get("id")==item["id"]:
                if hasattr(c,"mark_seen"): c.mark_seen()
                break
        DetailWindow(self.root, item)
        unseen = sum(1 for c in self._cards
                     if hasattr(c,"item") and not c.item.get("seen"))
        self._hdr_count.configure(
            text=t("unread_of", unread=unseen, total=len(self._cards)) if unseen
            else t("n_articles", n=len(self._cards)))

    def _switch_view(self):
        self._view_mode = self._view_var.get()
        self._reload()

    # ── Feed mgmt ──
    def _add_feed(self):
        url = simpledialog.askstring(t("add_feed_title"), t("add_feed_prompt"),
                                      parent=self.root)
        if url and url.strip():
            self.store.add_feed(url.strip())
            self._refresh_sidebar()
            self._select_feed(url.strip())

    def _del_feed(self, url):
        if messagebox.askyesno(t("del_feed_title"), t("del_feed_confirm",url=url),
                                parent=self.root):
            self.store.remove_feed(url)
            if self._active_feed == url: self._active_feed = None
            self._refresh_sidebar(); self._reload()

    def _toggle_pin(self, url, pinned):
        self.store.pin_feed(url, not pinned); self._refresh_sidebar()

    def _check_all(self):
        self._set_status(t("checking_all"))
        def worker():
            for f in self.store.get_feeds():
                for it in core.fetch_feed(f["url"]):
                    self.store.upsert(it, f["url"])
                time.sleep(0.3)
            self.root.after(0, self._reload)
            self.root.after(0, lambda: self._set_status(t("checked_all")))
        threading.Thread(target=worker, daemon=True).start()

    def _fetch_feed(self, url):
        items = core.fetch_feed(url)
        for it in items: self.store.upsert(it, url)
        self.root.after(0, self._reload)
        self.root.after(0, lambda: self._set_status(t("fetched", n=len(items), url=url)))

    # ── DNS ──
    def _open_dns(self):
        DNSScannerWindow(self.root, self._apply_dns)

    def _apply_dns(self, server):
        config.ACTIVE_DOH = server
        core.install_doh_resolver(server["ip"], server["host"])
        lat = f" ({server['latency_ms']}ms)" if server.get("latency_ms") else ""
        self._dns_lbl.configure(text=f"DNS: {server['name']}{lat}")
        self._set_status(t("dns_changed", name=server["name"]))

    # ── Theme ──
    def _toggle_theme(self):
        new = "light" if self._settings.get("theme","dark")=="dark" else "dark"
        self._settings["theme"] = new
        config.save_settings(self._settings)
        self._apply_settings_globals(rebuild=True)

    # ── Log ──
    def _open_log(self): LogWindow(self.root)

    # ── Settings ──
    def _open_settings(self):
        def on_save(s):
            self._settings = s
            config.save_settings(s)
            self._apply_settings_globals(rebuild=True)
        SettingsWindow(self.root, self._settings, on_save)

    # ── Internet ──
    def _on_net_update(self, r):
        self.root.after(0, self._update_net_ui, r)

    def _update_net_ui(self, r):
        label = r.get("label",""); color = r.get("color", C["text_secondary"])
        try:
            self._net_lbl.configure(text=f"🌐 {label}", fg=color)
            self._net_side_lbl.configure(text=f"🌐 {label}", fg=color)
        except: pass

    # ── Status ──
    def _set_status(self, msg):
        try: self._status_lbl.configure(text=msg)
        except: pass

    # ── Background ──
    def _start_bg(self):
        existing = {f["url"] for f in self.store.get_feeds()}
        for url in config.DEFAULT_FEEDS:
            if url not in existing: self.store.add_feed(url)
        self._refresh_sidebar()
        threading.Thread(target=self._initial_load, daemon=True).start()
        if config.CHECK_INTERVAL > 0:
            def auto():
                while True:
                    time.sleep(config.CHECK_INTERVAL)
                    for f in self.store.get_feeds():
                        for it in core.fetch_feed(f["url"]):
                            self.store.upsert(it, f["url"])
                    self.root.after(0, self._reload)
            threading.Thread(target=auto, daemon=True).start()

    def _initial_load(self):
        self.root.after(0, lambda: self._set_status("Fetching feeds..."))
        for f in self.store.get_feeds():
            for it in core.fetch_feed(f["url"]):
                self.store.upsert(it, f["url"])
        self.root.after(0, self._reload)
        self.root.after(0, lambda: self._set_status(t("ready")))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("980x700")
    root.minsize(740, 520)
    RSSApp(root)
    root.mainloop()
