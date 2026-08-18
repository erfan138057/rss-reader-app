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
        # Signal Modular: deep navy surfaces with teal status and vermilion breaking accents.
        "bg":            "#101827",
        "sidebar":       "#0B1220",
        "card":          "#172338",
        "card_seen":     "#131E2F",
        "card_hover":    "#20314B",
        "accent":        "#2DD4BF",
        "accent2":       "#7CE8DD",
        "accent_glow":   "#164E63",
        "text_primary":  "#F8FAFC",
        "text_secondary":"#9AAAC0",
        "text_seen":     "#65758D",
        "badge":         "#0F766E",
        "badge_new":     "#F06A5A",
        "separator":     "#23324A",
        "input_bg":      "#18253A",
        "btn":           "#1D9C93",
        "btn_hover":     "#147C75",
        "danger":        "#FB7185",
        "success":       "#34D399",
        "warning":       "#FBBF24",
        "panel":         "#141F31",
        "reddit_header": "#141F31",
        "reddit_card":   "#172338",
        "reddit_border": "#2A3B55",
        "tag_bg":        "#20314B",
        "tag_fg":        "#8BE9E0",
        "tag_video":     "#312E81",
        "tag_video_fg":  "#C4B5FD",
        "pin_color":     "#FBBF24",
        "active_feed":   "#1A3B4A",
        "breaking":      "#F06A5A",
        "surface2":      "#1B2A41",
    },
    "light": {
        "bg":            "#F3F6FA",
        "sidebar":       "#FFFFFF",
        "card":          "#FFFFFF",
        "card_seen":     "#F7F9FC",
        "card_hover":    "#EEF4F7",
        "accent":        "#0F8F86",
        "accent2":       "#138F87",
        "accent_glow":   "#CFF7F3",
        "text_primary":  "#172033",
        "text_secondary":"#64748B",
        "text_seen":     "#98A6B9",
        "badge":         "#0F8F86",
        "badge_new":     "#E65D4F",
        "separator":     "#DFE7F0",
        "input_bg":      "#EEF3F8",
        "btn":           "#0F8F86",
        "btn_hover":     "#0B726C",
        "danger":        "#E65D4F",
        "success":       "#0F9D75",
        "warning":       "#C77A13",
        "panel":         "#FFFFFF",
        "reddit_header": "#FFFFFF",
        "reddit_card":   "#FFFFFF",
        "reddit_border": "#DFE7F0",
        "tag_bg":        "#E7F6F4",
        "tag_fg":        "#0B726C",
        "tag_video":     "#F1EDFF",
        "tag_video_fg":  "#5B4AB8",
        "pin_color":     "#C77A13",
        "active_feed":   "#DDF5F1",
        "breaking":      "#E65D4F",
        "surface2":      "#F7FAFC",
    },
}
C = THEMES["dark"]

# fonts — rebuilt when font_size changes
def _fonts(size=9):
    return {
        "title":   ("Segoe UI", size+2, "bold"),
        "body":    ("Segoe UI", size),
        "meta":    ("Segoe UI", max(8, size-1)),
        "large":   ("Segoe UI", size+5, "bold"),
        "btn":     ("Segoe UI", size, "bold"),
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
    # Allow individual controls to override spacing without passing duplicate Tk options.
    padx = kw.pop("padx", 12)
    pady = kw.pop("pady", 6)
    b = tk.Button(parent, text=text, command=cmd,
                   bg=bg or C["btn"], fg=fg or "white",
                   font=F["btn"], relief="flat", borderwidth=0,
                   highlightthickness=0, takefocus=0, padx=padx, pady=pady,
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
    """
    Multi-strategy video player:
    1. VLC embedded (if libvlc is installed)
    2. System default player (os.startfile / xdg-open)
    3. Browser fallback (always works)
    """
    def __init__(self, parent, video_url: str, video_type: str, title: str,
                 prefer_internal: bool = False, external_player_path: str = ""):
        super().__init__(parent)
        self.title(t("video_title"))
        self.geometry("820x540")
        self.configure(bg=C["bg"])
        self._url  = video_url
        self._type = video_type
        self._prefer_internal = prefer_internal
        self._external_player_path = external_player_path.strip()
        self._player = None
        self._vol  = 100
        self._build(title)

    def _vlc_lib_ok(self) -> bool:
        try:
            inst = vlc.Instance()
            return inst is not None
        except Exception as e:
            core.LOG.warning(f"libvlc not loadable: {e}")
            return False

    def _build(self, title):
        hdr = tk.Frame(self, bg=C["sidebar"], pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title[:80], font=F["btn"],
                  fg=C["text_primary"], bg=C["sidebar"]).pack(side="left", padx=14)
        use_vlc = (self._prefer_internal and VLC_OK and self._vlc_lib_ok()
                   and self._type in ("direct", "redgifs"))
        if use_vlc:
            core.LOG.info("Video: optional embedded VLC player")
            self._build_vlc()
        else:
            # The default path deliberately delegates to the user's own system handler.
            # No bundled or pre-installed player is required.
            core.LOG.info(f"Video: system default handler ({self._type})")
            self._build_system_ui()
            self.after(200, self._open_system)

    # ── VLC ──
    def _build_vlc(self):
        self._vlc_frame = tk.Frame(self, bg="black")
        self._vlc_frame.pack(fill="both", expand=True)
        self._prog = ttk.Progressbar(self, mode="indeterminate")
        self._prog.pack(fill="x")
        ctrl = tk.Frame(self, bg=C["sidebar"], pady=8)
        ctrl.pack(fill="x")
        _btn(ctrl, "⏮-10s", lambda: self._seek(-10), bg=C["input_bg"], fg=C["text_primary"]).pack(side="left", padx=4)
        _btn(ctrl, "⏸▶",   self._toggle,             bg=C["btn"],      fg="white"           ).pack(side="left", padx=4)
        _btn(ctrl, "+10s⏭", lambda: self._seek(10),  bg=C["input_bg"], fg=C["text_primary"]).pack(side="left", padx=4)
        tk.Label(ctrl, text="🔈", bg=C["sidebar"], fg=C["text_secondary"], font=F["meta"]).pack(side="left", padx=(10,2))
        _btn(ctrl, "−", lambda: self._volume(-10), bg=C["input_bg"], fg=C["text_primary"], padx=6).pack(side="left", padx=1)
        self._vol_lbl = tk.Label(ctrl, text="100%", font=F["meta"], fg=C["text_secondary"], bg=C["sidebar"], width=5)
        self._vol_lbl.pack(side="left")
        _btn(ctrl, "+", lambda: self._volume(10),  bg=C["input_bg"], fg=C["text_primary"], padx=6).pack(side="left", padx=1)
        _btn(ctrl, "📂 System",  self._open_system,                  bg=C["input_bg"], fg=C["text_primary"]).pack(side="right", padx=4)
        _btn(ctrl, "🌐 Browser", lambda: webbrowser.open(self._url), bg=C["input_bg"], fg=C["text_primary"]).pack(side="right", padx=4)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._embed_vlc)

    def _embed_vlc(self):
        import sys
        try:
            self.update_idletasks()
            flags = [] if sys.platform.startswith("win") else ["--no-xlib"]
            instance = vlc.Instance(*flags)
            self._player = instance.media_player_new()
            self._player.set_media(instance.media_new(self._url))
            self._player.audio_set_volume(self._vol)
            self.update_idletasks()
            wid = self._vlc_frame.winfo_id()
            if sys.platform.startswith("win"):      self._player.set_hwnd(wid)
            elif sys.platform.startswith("darwin"): self._player.set_nsobject(wid)
            else:                                    self._player.set_xwindow(wid)
            self._player.play()
            self._prog.start(15)
            self.after(3000, lambda: self._prog.stop() if self.winfo_exists() else None)
            core.LOG.info(f"VLC playing: {self._url}")
        except Exception as e:
            core.LOG.error(f"VLC embed failed: {e}")
            if hasattr(self, "_prog"): self._prog.stop()
            self._open_system()

    # ── Online (YouTube/Vimeo/Redgifs) ──
    def _build_online(self):
        inner = tk.Frame(self, bg=C["bg"])
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="▶", font=("Segoe UI", 56), fg=C["accent"], bg=C["bg"]).pack(pady=30)
        tk.Label(inner, text=f"{self._type.title()} Video", font=F["large"],
                  fg=C["text_primary"], bg=C["bg"]).pack()
        short = self._url[:72]+"…" if len(self._url)>72 else self._url
        tk.Label(inner, text=short, font=F["meta"], fg=C["text_secondary"], bg=C["bg"]).pack(pady=6)
        row = tk.Frame(inner, bg=C["bg"]); row.pack(pady=14)
        _btn(row, "🌐 Open in Browser", lambda: webbrowser.open(self._url), bg=C["btn"]).pack(side="left", padx=8)
        _btn(row, "📂 System Player",   self._open_system, bg=C["input_bg"], fg=C["text_primary"]).pack(side="left", padx=4)
        self.after(150, lambda: webbrowser.open(self._url))

    # ── System player ──
    def _build_system_ui(self):
        inner = tk.Frame(self, bg=C["bg"])
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="📽️", font=("Segoe UI", 48), bg=C["bg"]).pack(pady=24)
        tk.Label(inner, text="Opening with your system default player…", font=F["large"],
                  fg=C["text_primary"], bg=C["bg"]).pack()
        short = self._url[:72]+"…" if len(self._url)>72 else self._url
        tk.Label(inner, text=short, font=F["meta"], fg=C["text_secondary"], bg=C["bg"]).pack(pady=6)
        row = tk.Frame(inner, bg=C["bg"]); row.pack(pady=14)
        _btn(row, "📂 Open with System Default", self._open_system, bg=C["btn"]).pack(side="left", padx=8)
        _btn(row, "🌐 Browser", lambda: webbrowser.open(self._url),
             bg=C["input_bg"], fg=C["text_primary"]).pack(side="left", padx=4)

    def _open_system(self):
        import sys, subprocess
        try:
            if self._external_player_path and os.path.isfile(self._external_player_path):
                subprocess.Popen([self._external_player_path, self._url])
                core.LOG.info(f"Custom video player: {self._external_player_path}")
            elif sys.platform.startswith("win"):
                # Windows opens the URL through the user's registered default application.
                os.startfile(self._url)
                core.LOG.info(f"Windows default video handler: {self._url}")
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", self._url])
                core.LOG.info(f"macOS default video handler: {self._url}")
            else:
                subprocess.Popen(["xdg-open", self._url])
                core.LOG.info(f"Linux default video handler: {self._url}")
        except Exception as e:
            core.LOG.error(f"System video handler failed: {e}")
            webbrowser.open(self._url)

    # ── Controls ──
    def _toggle(self):
        if self._player:
            if self._player.is_playing(): self._player.pause()
            else: self._player.play()

    def _stop(self):
        if self._player: self._player.stop()

    def _seek(self, seconds: int):
        if self._player:
            self._player.set_time(max(0, self._player.get_time() + seconds * 1000))

    def _volume(self, delta: int):
        if self._player:
            self._vol = max(0, min(200, self._vol + delta))
            self._player.audio_set_volume(self._vol)
            if hasattr(self, "_vol_lbl"): self._vol_lbl.configure(text=f"{self._vol}%")

    def _on_close(self):
        if self._player:
            try: self._player.stop()
            except: pass
        self.destroy()

# ---------------------------------------------------------------------------
# Detail Window (article)
# ---------------------------------------------------------------------------
class DetailWindow(tk.Toplevel):
    LONG_THRESHOLD = 300

    def __init__(self, parent, item: dict, store=None, prefer_internal_video: bool = False,
                 external_player_path: str = ""):
        super().__init__(parent)
        self.title(item.get("title","Article")[:60])
        self.geometry("740x580")
        self.configure(bg=C["bg"])
        self._item = item
        self._store = store
        self._prefer_internal_video = prefer_internal_video
        self._external_player_path = external_player_path
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
                                       item.get("title", ""),
                                       prefer_internal=self._prefer_internal_video,
                                       external_player_path=self._external_player_path),
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
        _btn(btn_row, "Reader Mode", lambda: ReaderWindow(self, item),
              bg=C["accent2"], fg=C["bg"]).pack(side="left", padx=8)

        # Bookmark toggle
        is_bm = bool(item.get("bookmarked"))
        self._bm_btn = _btn(
            btn_row,
            t("bookmark_remove") if is_bm else t("bookmark_add"),
            self._toggle_bookmark,
            bg=C.get("warning","#F59E0B") if is_bm else C["input_bg"],
            fg=C["bg"] if is_bm else C["text_primary"]
        )
        self._bm_btn.pack(side="left", padx=8)

        _btn(btn_row, t("close"), self.destroy,
              bg=C["input_bg"], fg=C["text_primary"]).pack(side="right")

    def _toggle_bookmark(self):
        if not self._store: return
        new_state = self._store.toggle_bookmark(self._item["id"])
        self._item["bookmarked"] = int(new_state)
        if new_state:
            self._bm_btn.configure(text=t("bookmark_remove"),
                                    bg=C.get("warning","#F59E0B"), fg=C["bg"])
        else:
            self._bm_btn.configure(text=t("bookmark_add"),
                                    bg=C["input_bg"], fg=C["text_primary"])

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
# Reader Mode Window
# ---------------------------------------------------------------------------
class ReaderWindow(tk.Toplevel):
    """Display article text extracted from the original page in a distraction-free view."""
    def __init__(self, parent, item: dict):
        super().__init__(parent)
        self.title("Reader Mode")
        self.geometry("760x640")
        self.configure(bg=C["bg"])
        self._item = item
        self._build()
        threading.Thread(target=self._load, daemon=True).start()

    def _build(self):
        header = tk.Frame(self, bg=C["sidebar"], pady=10)
        header.pack(fill="x")
        self._title = tk.Label(header, text=self._item.get("title", "Reader Mode"),
                               font=F["large"], fg=C["text_primary"], bg=C["sidebar"],
                               wraplength=680, justify="left", anchor="w")
        self._title.pack(fill="x", padx=16)
        self._status = tk.Label(header, text="Loading clean article…", font=F["meta"],
                                fg=C["text_secondary"], bg=C["sidebar"])
        self._status.pack(anchor="w", padx=16, pady=(4, 0))
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=14)
        self._text = tk.Text(body, font=F["body"], fg=C["text_primary"], bg=C["card"],
                             relief="flat", wrap="word", padx=18, pady=16)
        bar = ttk.Scrollbar(body, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=bar.set)
        self._text.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        _btn(self, t("close"), self.destroy, bg=C["input_bg"],
             fg=C["text_primary"]).pack(anchor="e", padx=16, pady=(0, 12))

    def _load(self):
        try:
            content = core.fetch_reader_content(self._item.get("link", ""))
            self.after(0, self._show_content, content)
        except Exception as exc:
            self.after(0, self._show_error, str(exc))

    def _show_content(self, content):
        self._title.configure(text=content.get("title") or self._item.get("title", "Reader Mode"))
        self._status.configure(text=content.get("url", ""))
        self._text.insert("1.0", content.get("text", ""))
        self._text.config(state="disabled")

    def _show_error(self, message):
        self._status.configure(text="Unable to load Reader Mode")
        self._text.insert("1.0", f"Reader Mode could not extract this article.\n\n{message}")
        self._text.config(state="disabled")

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
        self._notify_var = tk.BooleanVar(value=self._s.get("notifications", True))
        self._row(g, t("notifications_label"), lambda p: tk.Checkbutton(
            p, variable=self._notify_var, bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))

        # ── Feeds ──
        fd = self._section(inner, t("section_feeds"))

        self._sort_var = tk.StringVar(value=self._s.get("sort","newest"))
        self._row(fd, t("sort_label"), lambda p: ttk.Combobox(
            p, textvariable=self._sort_var,
            values=[t("sort_newest"), t("sort_oldest"), t("sort_popularity")],
            width=14, state="readonly").pack(side="left"))

        self._show_read_var = tk.BooleanVar(value=self._s.get("show_read", True))
        self._row(fd, t("show_read_label"), lambda p: tk.Checkbutton(
            p, variable=self._show_read_var,
            bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))

        # ── Display ──
        dp = self._section(inner, t("section_display"))

        self._font_var = tk.IntVar(value=int(self._s.get("font_size", 9)))
        self._font_value = tk.StringVar(value=str(self._font_var.get()))
        def make_font_slider(parent):
            ttk.Scale(parent, from_=8, to=16, orient="horizontal", length=130,
                      variable=self._font_var,
                      command=lambda value: self._font_value.set(str(int(float(value))))).pack(side="left")
            tk.Label(parent, textvariable=self._font_value, width=3, font=F["mono"],
                     fg=C["text_primary"], bg=C["bg"]).pack(side="left", padx=6)
        self._row(dp, t("font_size_label"), make_font_slider)

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
        self._auto_scroll_var = tk.BooleanVar(value=self._s.get("auto_scroll", False))
        self._row(dp, t("auto_scroll"), lambda p: tk.Checkbutton(
            p, variable=self._auto_scroll_var,
            bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))
        self._auto_scroll_speed_var = tk.IntVar(value=int(self._s.get("auto_scroll_speed", 2)))
        self._row(dp, t("auto_scroll_speed"), lambda p: ttk.Scale(
            p, from_=1, to=8, orient="horizontal", length=130,
            variable=self._auto_scroll_speed_var).pack(side="left"))

        # ── Video ──
        vd = self._section(inner, t("section_video"))

        self._vid_int_var = tk.BooleanVar(value=self._s.get("video_internal", False))
        self._row(vd, t("video_internal"), lambda p: tk.Checkbutton(
            p, variable=self._vid_int_var,
            bg=C["bg"], selectcolor=C["input_bg"],
            activebackground=C["bg"]).pack(side="left"))
        self._player_path_var = tk.StringVar(value=self._s.get("external_player_path", ""))
        def make_player_picker(parent):
            tk.Entry(parent, textvariable=self._player_path_var, width=22,
                     bg=C["input_bg"], fg=C["text_primary"], relief="flat",
                     font=F["meta"], insertbackground=C["text_primary"]).pack(side="left", ipady=3)
            _btn(parent, t("browse"), lambda: self._choose_player_path(),
                 bg=C["input_bg"], fg=C["text_primary"], padx=7, pady=3).pack(side="left", padx=5)
        self._row(vd, t("video_player_path"), make_player_picker)

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

    def _choose_player_path(self):
        path = filedialog.askopenfilename(
            parent=self, title=t("video_player_path"),
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")])
        if path:
            self._player_path_var.set(path)

    def _save(self):
        theme_map = {t("theme_dark"): "dark", t("theme_light"): "light",
                     "dark": "dark", "light": "light"}
        sort_map  = {t("sort_newest"): "newest", t("sort_oldest"): "oldest",
                     t("sort_popularity"): "popularity", "newest": "newest",
                     "oldest": "oldest", "popularity": "popularity"}
        self._s.update({
            "language":       self._lang_var.get(),
            "theme":          theme_map.get(self._theme_var.get(), "dark"),
            "check_interval": int(self._interval_var.get() or 300),
            "sort":           sort_map.get(self._sort_var.get(), "newest"),
            "show_read":      self._show_read_var.get(),
            "load_images":    self._img_var.get(),
            "font_size":      int(self._font_var.get() or 9),
            "card_style":     self._card_var.get(),
            "notifications":  self._notify_var.get(),
            "auto_scroll":    self._auto_scroll_var.get(),
            "auto_scroll_speed": int(self._auto_scroll_speed_var.get() or 2),
            "video_internal": self._vid_int_var.get(),
            "external_player_path": self._player_path_var.get().strip(),
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
    # Signal Modular cards are intentionally spacious enough for scanning at a glance.
    TW, TH = 132, 92

    def __init__(self, master, item, on_click, on_context=None, load_images=True, **kw):
        seen = bool(item.get("seen"))
        bg = C["card_seen"] if seen else C["card"]
        super().__init__(master, bg=bg, cursor="hand2", **kw)
        self.item = item
        self.on_click = on_click
        self.on_context = on_context
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
        self.configure(highlightthickness=1, highlightbackground=C["reddit_border"], highlightcolor=C["accent"])

        inner = tk.Frame(self, bg=self._bg)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        accent = C["accent"] if not seen else C["separator"]
        tk.Frame(inner, height=3, bg=accent).pack(fill="x")
        body = tk.Frame(inner, bg=self._bg)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        self.img_lbl = tk.Label(body, bg=self._bg, image=self._ph, width=self.TW, height=self.TH)
        self.img_lbl.image = self._ph
        self.img_lbl.pack(side="left", padx=(0, 12), anchor="n")

        copy = tk.Frame(body, bg=self._bg)
        copy.pack(side="left", fill="both", expand=True, anchor="n")
        from urllib.parse import urlparse as up
        domain = up(self.item.get("feed", "")).netloc
        eyebrow = tk.Frame(copy, bg=self._bg)
        eyebrow.pack(fill="x", anchor="w", pady=(0, 5))
        if not seen:
            tk.Label(eyebrow, text="●  UNREAD", font=F["tag"], fg=C["accent"],
                     bg=self._bg).pack(side="left")
        if domain:
            tk.Label(eyebrow, text=("  " if not seen else "   ") + domain.upper()[:22],
                     font=F["meta"], fg=mc, bg=self._bg).pack(side="left")
        if self.item.get("video_url"):
            tk.Label(eyebrow, text="  ▶", font=F["meta"], fg=C["tag_video_fg"],
                     bg=self._bg).pack(side="left")

        tk.Label(copy, text=self.item.get("title", ""), font=F["title"], fg=tc,
                 bg=self._bg, anchor="w", justify="left", wraplength=260).pack(anchor="w")
        sm = self.item.get("summary", "")
        if sm:
            tk.Label(copy, text=sm[:100] + ("…" if len(sm) > 100 else ""), font=F["body"],
                     fg=mc, bg=self._bg, anchor="w", justify="left", wraplength=265).pack(anchor="w", pady=(4, 0))
        pub = self.item.get("published", "")[:16]
        tk.Label(copy, text=f"{pub}  ·  {domain}" if domain else pub, font=F["meta"],
                 fg=mc, bg=self._bg, anchor="w").pack(anchor="w", pady=(7, 0))

        is_bm = bool(self.item.get("bookmarked"))
        bm_btn = tk.Button(body, text="▮" if is_bm else "▯", font=("Segoe UI", 13),
                           bg=self._bg, fg=C["warning"] if is_bm else C["text_seen"], relief="flat",
                           padx=3, pady=2, command=self._toggle_bookmark)
        bm_btn.pack(side="right", anchor="n")
        self._bm_btn = bm_btn
        for w in (inner, body, copy, eyebrow, self.img_lbl): self._bw(w)
        for w in copy.winfo_children() + eyebrow.winfo_children(): self._bw(w)

    def _bw(self, w):
        w.bind("<Button-1>", self._clicked)
        w.bind("<Button-3>", self._context)
        w.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        w.bind("<Leave>",    lambda e: self._sbg(self._bg))

    def _bind_all(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Button-3>", self._context)
        self.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        self.bind("<Leave>",    lambda e: self._sbg(self._bg))
        for w in self.winfo_children():
            if w is not getattr(self, "_bm_btn", None):
                self._bw(w)

    def _toggle_bookmark(self):
        if not hasattr(self, "_store"): return
        new_state = self._store.toggle_bookmark(self.item["id"])
        self.item["bookmarked"] = int(new_state)
        self._bm_btn.configure(
            fg=C.get("warning","#F59E0B") if new_state else C["text_seen"])

    def set_store(self, store):
        self._store = store

    def _sbg(self, color):
        self.configure(bg=color)
        def paint(widget):
            for child in widget.winfo_children():
                try: child.configure(bg=color)
                except: pass
                paint(child)
        paint(self)

    def _clicked(self, e=None): self.on_click(self.item)

    def _context(self, event):
        if self.on_context:
            self.on_context(event, self.item)
            return "break"

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

    def update_bookmark_btn(self, is_bookmarked: bool):
        """Update bookmark button appearance after toggle."""
        for w in self.winfo_children():
            if isinstance(w, tk.Button) and "🔖" in str(w.cget("text")):
                w.configure(
                    text="🔖" if is_bookmarked else "🔖",
                    fg=C["warning"] if is_bookmarked else C["text_seen"]
                )
                break

# ---------------------------------------------------------------------------
# Top Story Card — featured horizontal storytelling layer
# ---------------------------------------------------------------------------
class TopStoryCard(tk.Frame):
    IW, IH = 190, 96

    def __init__(self, master, item, on_click, on_context=None, load_images=True, **kw):
        super().__init__(master, bg=C["card"], cursor="hand2", highlightthickness=1,
                         highlightbackground=C["reddit_border"], **kw)
        self.item = item
        self.on_click = on_click
        self.on_context = on_context
        self._photo = None
        self._ph = make_placeholder(self.IW, self.IH)
        self._build()
        self._bind_all()
        if load_images:
            self._load_img_async()

    def _build(self):
        image_frame = tk.Frame(self, bg=C["card"])
        image_frame.pack(fill="x", padx=1, pady=1)
        self.img_lbl = tk.Label(image_frame, image=self._ph, bg=C["card"],
                                width=self.IW, height=self.IH)
        self.img_lbl.image = self._ph
        self.img_lbl.pack(fill="x")
        body = tk.Frame(self, bg=C["card"])
        body.pack(fill="both", expand=True, padx=10, pady=9)
        label = "BREAKING NEWS" if not self.item.get("seen") else "TOP STORY"
        tk.Label(body, text=label, font=F["tag"], fg=C["breaking"] if not self.item.get("seen") else C["accent"],
                 bg=C["card"]).pack(anchor="w")
        tk.Label(body, text=self.item.get("title", ""), font=F["title"], fg=C["text_primary"],
                 bg=C["card"], anchor="w", justify="left", wraplength=185).pack(anchor="w", pady=(4, 0))
        from urllib.parse import urlparse as up
        domain = up(self.item.get("feed", "")).netloc
        tk.Label(body, text=domain.upper()[:22] or "RSS READER", font=F["meta"],
                 fg=C["text_secondary"], bg=C["card"]).pack(anchor="w", pady=(8, 0))
        for widget in (self, image_frame, self.img_lbl, body):
            widget.bind("<Button-1>", self._clicked)
            widget.bind("<Button-3>", self._context)
            widget.bind("<Enter>", lambda e: self._paint(C["card_hover"]))
            widget.bind("<Leave>", lambda e: self._paint(C["card"]))
        for widget in body.winfo_children():
            widget.bind("<Button-1>", self._clicked)
            widget.bind("<Button-3>", self._context)
            widget.bind("<Enter>", lambda e: self._paint(C["card_hover"]))
            widget.bind("<Leave>", lambda e: self._paint(C["card"]))

    def _paint(self, color):
        self.configure(bg=color)
        def walk(widget):
            for child in widget.winfo_children():
                try: child.configure(bg=color)
                except: pass
                walk(child)
        walk(self)

    def _bind_all(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Button-3>", self._context)

    def _clicked(self, event=None):
        self.on_click(self.item)

    def _context(self, event):
        if self.on_context:
            self.on_context(event, self.item)
            return "break"

    def _load_img_async(self):
        def worker():
            url = self.item.get("image_url", "")
            data = core.fetch_image_bytes(url) if url else b""
            if not data and self.item.get("link"):
                og = core.fetch_og_image(self.item["link"])
                if og:
                    self.item["image_url"] = og
                    data = core.fetch_image_bytes(og)
            if data:
                photo = resize_image(data, self.IW, self.IH)
                if photo:
                    self.after(0, self._set_image, photo)
        threading.Thread(target=worker, daemon=True).start()

    def _set_image(self, photo):
        self._photo = photo
        try:
            self.img_lbl.configure(image=photo)
            self.img_lbl.image = photo
        except: pass

# ---------------------------------------------------------------------------
# Reddit Card
# ---------------------------------------------------------------------------
class RedditCard(tk.Frame):
    IW, IH = 160, 100

    def __init__(self, master, item, index, on_click, on_context=None, load_images=True, **kw):
        bg = C["reddit_card"]
        super().__init__(master, bg=bg, cursor="hand2", **kw)
        self.item = item
        self.on_click = on_click
        self.on_context = on_context
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
            tk.Label(tag_row, text=f"🌐 {domain}", font=F["tag"],
                      fg=C["tag_fg"], bg=C["tag_bg"],
                      padx=6, pady=2).pack(side="left", padx=(0,4))
        if self.item.get("video_url"):
            vt = self.item.get("video_type","")
            icon = "▶ YouTube" if vt=="youtube" else ("▶ Vimeo" if vt=="vimeo" else "▶ Video")
            tk.Label(tag_row, text=icon, font=F["tag"],
                      fg=C.get("tag_video_fg","#C4B5FD"),
                      bg=C.get("tag_video","#7C3AED"),
                      padx=6, pady=2).pack(side="left", padx=2)
        if not bool(self.item.get("seen")):
            tk.Label(tag_row, text="NEW", font=F["tag"],
                      fg="white", bg=C.get("badge_new", C["badge"]),
                      padx=6, pady=2).pack(side="left", padx=2)

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
        w.bind("<Button-3>", self._context)
        w.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        w.bind("<Leave>",    lambda e: self._sbg(self._bg))

    def _bind_all(self):
        self.bind("<Button-1>", self._clicked)
        self.bind("<Button-3>", self._context)
        self.bind("<Enter>",    lambda e: self._sbg(C["card_hover"]))
        self.bind("<Leave>",    lambda e: self._sbg(self._bg))
        for w in self.winfo_children(): self._bw(w)

    def _sbg(self, color):
        self.configure(bg=color)
        for w in self.winfo_children():
            try: w.configure(bg=color)
            except: pass

    def _clicked(self, e=None): self.on_click(self.item)

    def _context(self, event):
        if self.on_context:
            self.on_context(event, self.item)
            return "break"

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
        self._focused_item = None
        self._auto_scroll_job = None
        self.root.bind_all("<space>", self._keyboard_shortcut)
        self.root.bind_all("<Key-b>", self._keyboard_shortcut)
        self.root.bind_all("<Key-o>", self._keyboard_shortcut)

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
        s.configure("TScrollbar", background=C["surface2"], troughcolor=C["bg"],
                     arrowcolor=C["text_secondary"], bordercolor=C["separator"], lightcolor=C["surface2"], darkcolor=C["surface2"])
        s.configure("TCombobox", fieldbackground=C["surface2"], background=C["surface2"],
                     foreground=C["text_primary"], arrowcolor=C["text_secondary"],
                     bordercolor=C["separator"], selectbackground=C["accent"], selectforeground=C["sidebar"])
        s.map("TCombobox", fieldbackground=[("readonly", C["surface2"])],
              background=[("readonly", C["surface2"])], foreground=[("readonly", C["text_primary"])])

    # ── Layout ──
    def _build(self):
        self.root.title(t("app_title"))
        self.root.configure(bg=C["bg"])
        self.root.minsize(1180, 680)

        # Signal Modular keeps navigation compact to prioritize the content canvas.
        self.sidebar = tk.Frame(self.root, bg=C["sidebar"], width=196,
                                highlightthickness=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        self.main = tk.Frame(self.root, bg=C["bg"])
        self.main.pack(side="left", fill="both", expand=True)
        self._build_main()
        if self._settings.get("auto_scroll", False):
            self.root.after(500, self._schedule_auto_scroll)

    def _build_sidebar(self):
        # Brand block: compact and intentional rather than a toolbar of utilities.
        logo = tk.Frame(self.sidebar, bg=C["sidebar"], pady=18)
        logo.pack(fill="x", padx=16)
        mark = tk.Label(logo, text="⌁", font=("Segoe UI", 25, "bold"),
                        fg=C["accent"], bg=C["sidebar"], width=2)
        mark.pack(side="left")
        brand = tk.Frame(logo, bg=C["sidebar"])
        brand.pack(side="left", padx=(7, 0))
        tk.Label(brand, text=t("app_title"), font=F["large"],
                 fg=C["text_primary"], bg=C["sidebar"]).pack(anchor="w")
        tk.Label(brand, text="YOUR DAILY SIGNAL", font=F["meta"],
                 fg=C["text_seen"], bg=C["sidebar"]).pack(anchor="w")
        tk.Button(logo, text="☀" if self._settings.get("theme") == "dark" else "◐",
                  font=("Segoe UI", 11), bg=C["sidebar"], fg=C["text_secondary"],
                  relief="flat", command=self._toggle_theme).pack(side="right")

        nav = tk.Frame(self.sidebar, bg=C["sidebar"])
        nav.pack(fill="x", padx=12, pady=(5, 10))
        self._sb_btn(nav, "◉  " + t("all_feeds"), lambda: self._select_feed(None), selected=True)
        self._sb_btn(nav, "▣  " + t("bookmarks"), self._show_bookmarks)

        quick = tk.Frame(self.sidebar, bg=C["sidebar"])
        quick.pack(fill="x", padx=16, pady=(2, 14))
        _btn(quick, "+  " + t("add_feed"), self._add_feed,
             bg=C["btn"], fg="white", padx=9, pady=5).pack(side="left")
        _btn(quick, "↻", self._check_all, bg=C["surface2"],
             fg=C["text_primary"], padx=10, pady=5).pack(side="left", padx=6)
        _btn(quick, "⚙", self._open_settings, bg=C["surface2"],
             fg=C["text_primary"], padx=10, pady=5).pack(side="right")

        tk.Label(self.sidebar, text="FEED COLLECTIONS", font=F["meta"],
                 fg=C["text_seen"], bg=C["sidebar"]).pack(anchor="w", padx=18, pady=(0, 6))
        wrap = tk.Frame(self.sidebar, bg=C["sidebar"])
        wrap.pack(fill="both", expand=True)
        cv = tk.Canvas(wrap, bg=C["sidebar"], highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vsb.set)
        cv.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._feed_inner = tk.Frame(cv, bg=C["sidebar"])
        cw = cv.create_window((0, 0), window=self._feed_inner, anchor="nw")
        self._feed_inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(cw, width=e.width))

        utility = tk.Frame(self.sidebar, bg=C["sidebar"])
        utility.pack(fill="x", padx=12, pady=(8, 2))
        for label_key, cmd in [("mark_all_read", self._mark_all_read),
                               ("import_opml", self._import_opml),
                               ("export_opml", self._export_opml),
                               ("export_bookmarks", self._export_bookmarks),
                               ("dns_scanner", self._open_dns),
                               ("log", self._open_log)]:
            self._sb_btn(utility, t(label_key), cmd, compact=True)

        bot = tk.Frame(self.sidebar, bg=C["sidebar"], highlightthickness=1,
                       highlightbackground=C["separator"])
        bot.pack(side="bottom", fill="x", padx=12, pady=12)
        self._dns_lbl = tk.Label(bot, text=f"DNS · {config.ACTIVE_DOH['name']}",
                                  font=F["meta"], fg=C["text_secondary"], bg=C["sidebar"])
        self._dns_lbl.pack(anchor="w", padx=10, pady=(7, 1))
        self._net_side_lbl = tk.Label(bot, text="● " + t("net_checking"), font=F["meta"],
                                      fg=C["success"], bg=C["sidebar"])
        self._net_side_lbl.pack(anchor="w", padx=10, pady=(0, 7))

    def _sb_btn(self, parent, text, cmd, selected=False, compact=False):
        bg = C["active_feed"] if selected else C["sidebar"]
        fg = C["text_primary"] if selected else C["text_secondary"]
        btn = tk.Button(parent, text=text, font=F["meta"] if compact else F["btn"],
                         bg=bg, fg=fg, relief="flat", borderwidth=0, highlightthickness=0,
                         anchor="w", padx=10, pady=4 if compact else 7,
                         activebackground=C["card_hover"], activeforeground=C["text_primary"], command=cmd)
        btn.pack(fill="x", pady=1)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=C["card_hover"], fg=C["text_primary"]))
        btn.bind("<Leave>", lambda e, b=btn, base=bg, color=fg: b.configure(bg=base, fg=color))

    def _build_main(self):
        # A composed, three-layer workspace replaces the old dense global toolbar.
        shell = tk.Frame(self.main, bg=C["bg"])
        shell.pack(fill="both", expand=True, padx=22, pady=(18, 10))

        self._hdr = tk.Frame(shell, bg=C["bg"])
        self._hdr.pack(fill="x")
        title_box = tk.Frame(self._hdr, bg=C["bg"])
        title_box.pack(side="left")
        self._hdr_title = tk.Label(title_box, text=t("all_news"), font=F["large"],
                                    fg=C["text_primary"], bg=C["bg"])
        self._hdr_title.pack(anchor="w")
        self._hdr_count = tk.Label(title_box, text="", font=F["meta"],
                                   fg=C["text_secondary"], bg=C["bg"])
        self._hdr_count.pack(anchor="w", pady=(1, 0))

        actions = tk.Frame(self._hdr, bg=C["bg"])
        actions.pack(side="right", pady=4)
        self._auto_scroll_var = tk.BooleanVar(value=self._settings.get("auto_scroll", False))
        tk.Checkbutton(actions, text=t("auto_scroll"), variable=self._auto_scroll_var,
                       command=self._toggle_auto_scroll, font=F["meta"], fg=C["text_secondary"],
                       bg=C["bg"], selectcolor=C["input_bg"], activebackground=C["bg"],
                       activeforeground=C["text_primary"]).pack(side="left", padx=8)
        _btn(actions, "✓  " + t("mark_all_read"), self._mark_all_read,
             bg=C["surface2"], fg=C["text_primary"], padx=10, pady=5).pack(side="left", padx=4)

        search_row = tk.Frame(shell, bg=C["panel"], highlightthickness=1,
                              highlightbackground=C["separator"])
        search_row.pack(fill="x", pady=(18, 10))
        tk.Label(search_row, text="⌕", fg=C["text_secondary"], bg=C["panel"],
                 font=("Segoe UI", 18)).pack(side="left", padx=(14, 7))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._reload())
        search = tk.Entry(search_row, textvariable=self._search_var, font=F["body"],
                          bg=C["panel"], fg=C["text_primary"], relief="flat",
                          insertbackground=C["text_primary"])
        search.pack(side="left", fill="x", expand=True, pady=10)
        _btn(search_row, "Filters", self._toggle_filter_panel, bg=C["surface2"],
             fg=C["text_primary"], padx=10, pady=4).pack(side="right", padx=8)

        toolbar = tk.Frame(shell, bg=C["bg"])
        toolbar.pack(fill="x", pady=(0, 12))
        self._view_var = tk.StringVar(value=self._view_mode)
        for lbl, val in [("All stories", "telegram"), ("Timeline", "reddit")]:
            tk.Radiobutton(toolbar, text=lbl, value=val, variable=self._view_var,
                           font=F["btn"], fg=C["text_primary"], bg=C["surface2"],
                           selectcolor=C["accent"], activebackground=C["surface2"],
                           activeforeground=C["text_primary"], indicatoron=0, borderwidth=0,
                           highlightthickness=0, padx=10, pady=5,
                           command=self._switch_view).pack(side="left", padx=(0, 7))
        self._show_read_var = tk.BooleanVar(value=self._settings.get("show_read", True))
        tk.Checkbutton(toolbar, text=t("show_read"), variable=self._show_read_var,
                       font=F["meta"], fg=C["text_secondary"], bg=C["bg"],
                       selectcolor=C["input_bg"], activebackground=C["bg"], command=self._reload).pack(side="left", padx=8)
        self._sort_var = tk.StringVar(value=self._settings.get("sort", "newest"))
        ttk.Combobox(toolbar, textvariable=self._sort_var, width=15, state="readonly",
                     values=[t("sort_newest"), t("sort_oldest"), t("sort_popularity")]).pack(side="right")
        self._sort_var.trace_add("write", lambda *a: self._reload())
        tk.Label(toolbar, text="SORT", font=F["meta"], fg=C["text_seen"], bg=C["bg"]).pack(side="right", padx=7)

        self._filters_wrap = tk.Frame(shell, bg=C["panel"], highlightthickness=1,
                                      highlightbackground=C["separator"])
        self._unread_only_var = tk.BooleanVar(value=False)
        self._bookmarked_only_var = tk.BooleanVar(value=False)
        for label, variable in [(t("unread_only"), self._unread_only_var),
                                (t("bookmarked_only"), self._bookmarked_only_var)]:
            tk.Checkbutton(self._filters_wrap, text=label, variable=variable, command=self._reload,
                           font=F["meta"], fg=C["text_secondary"], bg=C["panel"],
                           selectcolor=C["input_bg"], activebackground=C["panel"]).pack(side="left", padx=10, pady=8)
        self._from_date_var = tk.StringVar(); self._to_date_var = tk.StringVar()
        for label, variable in [(t("from_date"), self._from_date_var), (t("to_date"), self._to_date_var)]:
            tk.Label(self._filters_wrap, text=label, font=F["meta"], fg=C["text_seen"],
                     bg=C["panel"]).pack(side="left", padx=(8, 3))
            tk.Entry(self._filters_wrap, textvariable=variable, width=12, font=F["meta"],
                     bg=C["input_bg"], fg=C["text_primary"], relief="flat",
                     insertbackground=C["text_primary"]).pack(side="left", padx=(0, 4), ipady=3)
            variable.trace_add("write", lambda *args: self._reload())

        workspace = tk.Frame(shell, bg=C["bg"])
        workspace.pack(fill="both", expand=True)
        # Pack the fixed insight rail first so the central feed cannot consume its width.
        self._insight = tk.Frame(workspace, bg=C["panel"], width=186,
                                 highlightthickness=1, highlightbackground=C["separator"])
        self._insight.pack(side="right", fill="y", padx=(14, 0))
        self._insight.pack_propagate(False)
        self._content = tk.Frame(workspace, bg=C["bg"])
        self._content.pack(side="left", fill="both", expand=True)
        self._build_insight_panel()
        self._build_content_area()

        sb = tk.Frame(self.main, bg=C["sidebar"], highlightthickness=1,
                      highlightbackground=C["separator"])
        sb.pack(fill="x", side="bottom")
        self._status_lbl = tk.Label(sb, text="●  " + t("ready"), font=F["meta"],
                                    fg=C["text_secondary"], bg=C["sidebar"], anchor="w")
        self._status_lbl.pack(side="left", padx=16, pady=6)
        self._net_lbl = tk.Label(sb, text="●  ...", font=F["meta"], fg=C["success"],
                                 bg=C["sidebar"], anchor="e")
        self._net_lbl.pack(side="right", padx=16, pady=6)

    def _toggle_filter_panel(self):
        if self._filters_wrap.winfo_ismapped():
            self._filters_wrap.pack_forget()
        else:
            self._filters_wrap.pack(fill="x", pady=(0, 10), before=self._content)

    def _build_insight_panel(self):
        tk.Label(self._insight, text="SIGNAL", font=F["btn"], fg=C["text_primary"],
                 bg=C["panel"]).pack(anchor="w", padx=15, pady=(16, 2))
        tk.Label(self._insight, text="YOUR READING PULSE", font=F["meta"], fg=C["text_seen"],
                 bg=C["panel"]).pack(anchor="w", padx=15)
        ring = tk.Canvas(self._insight, width=90, height=90, bg=C["panel"],
                         highlightthickness=0)
        ring.pack(pady=(16, 6))
        ring.create_oval(12, 12, 78, 78, outline=C["separator"], width=7)
        ring.create_arc(12, 12, 78, 78, start=90, extent=250, style="arc",
                        outline=C["accent"], width=7)
        self._insight_count = ring.create_text(45, 40, text="0", fill=C["text_primary"],
                                               font=("Segoe UI", 16, "bold"))
        ring.create_text(45, 59, text="UNREAD", fill=C["text_seen"], font=F["meta"])
        self._insight_ring = ring
        tk.Frame(self._insight, height=1, bg=C["separator"]).pack(fill="x", padx=15, pady=12)
        tk.Label(self._insight, text="TOPICS", font=F["meta"], fg=C["text_seen"],
                 bg=C["panel"]).pack(anchor="w", padx=15, pady=(0, 7))
        self._topic_box = tk.Frame(self._insight, bg=C["panel"])
        self._topic_box.pack(fill="x", padx=13)
        for topic in ("World", "Technology", "Business", "Culture"):
            tk.Label(self._topic_box, text=topic, font=F["meta"], bg=C["surface2"],
                     fg=C["text_secondary"], padx=8, pady=5).pack(fill="x", pady=3)
        tk.Frame(self._insight, height=1, bg=C["separator"]).pack(fill="x", padx=15, pady=14)
        tk.Label(self._insight, text="TIP", font=F["meta"], fg=C["text_seen"],
                 bg=C["panel"]).pack(anchor="w", padx=15)
        tk.Label(self._insight, text="Save stories to build your reading queue.", font=F["body"],
                 fg=C["text_secondary"], bg=C["panel"], wraplength=148, justify="left").pack(anchor="w", padx=15, pady=(5, 0))

    def _update_insight_panel(self, items):
        if hasattr(self, "_insight_ring"):
            unread = sum(1 for item in items if not item.get("seen"))
            self._insight_ring.itemconfigure(self._insight_count, text=str(unread))

    def _build_content_area(self):
        for w in self._content.winfo_children(): w.destroy()
        self._sf = ScrollableFrame(self._content, bg=C["bg"])
        self._sf.pack(fill="both", expand=True)

    # ── Sidebar feed list ──
    def _refresh_sidebar(self):
        for w in self._feed_inner.winfo_children(): w.destroy()
        self._feed_row(t("all_feeds"), None)
        unread_counts = self.store.get_unread_counts()
        grouped = {}
        for feed in self.store.get_feeds():
            grouped.setdefault(feed.get("category") or "عمومی", []).append(feed)
        for category, feeds in grouped.items():
            tk.Label(self._feed_inner, text=category.upper(), font=F["meta"],
                     fg=C["accent2"], bg=C["sidebar"]).pack(anchor="w", padx=14, pady=(9, 2))
            for f in feeds:
                from urllib.parse import urlparse as up
                domain = f.get("title") or up(f["url"]).netloc or f["url"][:26]
                prefix = "📌 " if f["pinned"] else "  "
                count = unread_counts.get(f["url"], 0)
                suffix = f"  ({count})" if count else ""
                self._feed_row(prefix + domain + suffix, f["url"], f["pinned"])

    def _feed_row(self, text, url, pinned=False):
        is_active = url == self._active_feed
        bg = C["active_feed"] if is_active else C["sidebar"]
        fg = C["text_primary"] if is_active else C["text_secondary"]
        row = tk.Frame(self._feed_inner, bg=bg)
        row.pack(fill="x", padx=10, pady=1)
        if is_active:
            tk.Frame(row, width=3, bg=C["accent"]).pack(side="left", fill="y", padx=(0, 7))
        else:
            tk.Label(row, text="•", font=F["body"], fg=C["accent"] if pinned else C["text_seen"],
                     bg=bg, width=2).pack(side="left")
        btn = tk.Button(row, text=text, font=F["btn"], bg=bg, fg=fg, relief="flat",
                         borderwidth=0, highlightthickness=0, anchor="w", padx=3, pady=6, activebackground=C["card_hover"],
                         activeforeground=C["text_primary"], command=lambda u=url: self._select_feed(u))
        btn.pack(side="left", fill="x", expand=True)
        def hover(on):
            color = C["card_hover"] if on else bg
            row.configure(bg=color); btn.configure(bg=color, fg=C["text_primary"] if on else fg)
            for child in row.winfo_children():
                try: child.configure(bg=color)
                except: pass
        btn.bind("<Enter>", lambda e: hover(True)); btn.bind("<Leave>", lambda e: hover(False))
        if url:
            tk.Button(row, text="⋯", font=("Segoe UI", 11), bg=bg, fg=C["text_seen"],
                      relief="flat", padx=4, pady=1,
                      command=lambda u=url, p=pinned: self._show_feed_menu(u, p)).pack(side="right")

    def _show_feed_menu(self, url, pinned):
        menu = tk.Menu(self.root, tearoff=0, bg=C["card"], fg=C["text_primary"],
                       activebackground=C["accent"], activeforeground=C["sidebar"])
        menu.add_command(label="Unpin feed" if pinned else "Pin feed",
                         command=lambda: self._toggle_pin(url, pinned))
        menu.add_separator()
        menu.add_command(label="Remove feed", command=lambda: self._del_feed(url))
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()

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
        q = self._search_var.get() if hasattr(self, "_search_var") else ""
        show = self._show_read_var.get() if hasattr(self, "_show_read_var") else True
        sort = self._sort_var.get() if hasattr(self, "_sort_var") else "newest"
        mode = self._view_var.get() if hasattr(self, "_view_var") else "telegram"
        unread_only = (not show) or (self._unread_only_var.get() if hasattr(self, "_unread_only_var") else False)
        bookmarked_only = self._bookmarked_only_var.get() if hasattr(self, "_bookmarked_only_var") else False
        start_date = self._from_date_var.get().strip() if hasattr(self, "_from_date_var") else ""
        end_date = self._to_date_var.get().strip() if hasattr(self, "_to_date_var") else ""
        load_img = self._settings.get("load_images", True)

        # Bookmarks view remains compatible with all sorting options.
        if self._active_feed == "__bookmarks__":
            items = self.store.search_items(q, None, sort, unread_only, True, start_date, end_date)
        else:
            items = self.store.search_items(q, self._active_feed, sort, unread_only,
                                            bookmarked_only, start_date, end_date)
        for w in self._sf.inner.winfo_children(): w.destroy()
        self._cards = []

        if not items:
            empty_msg = t("bookmark_empty") if self._active_feed == "__bookmarks__" else t("no_articles")
            tk.Label(self._sf.inner, text=empty_msg, font=F["body"],
                      fg=C["text_secondary"], bg=C["bg"]).pack(pady=60)
        elif mode == "reddit":
            for i, item in enumerate(items, 1):
                card = RedditCard(self._sf.inner, item, i,
                                   on_click=self._open_item, on_context=self._show_card_menu,
                                   load_images=load_img)
                card.pack(fill="x", padx=4, pady=2)
                self._cards.append(card)
        else:
            featured = items[:3]
            remaining = items[3:] or items
            section = tk.Frame(self._sf.inner, bg=C["bg"])
            section.pack(fill="x", padx=2, pady=(2, 9))
            tk.Label(section, text="TOP STORIES", font=F["btn"], fg=C["text_primary"],
                     bg=C["bg"]).pack(side="left")
            tk.Label(section, text="A QUICK VIEW OF WHAT MATTERS", font=F["meta"],
                     fg=C["text_seen"], bg=C["bg"]).pack(side="left", padx=10)
            featured_grid = tk.Frame(self._sf.inner, bg=C["bg"])
            featured_grid.pack(fill="x", pady=(0, 18))
            for col in range(3):
                featured_grid.grid_columnconfigure(col, weight=1, uniform="featured")
            for col, item in enumerate(featured):
                card = TopStoryCard(featured_grid, item, on_click=self._open_item,
                                    on_context=self._show_card_menu, load_images=load_img)
                card.grid(row=0, column=col, sticky="nsew", padx=4)
                self._cards.append(card)

            latest_label = tk.Frame(self._sf.inner, bg=C["bg"])
            latest_label.pack(fill="x", padx=2, pady=(0, 8))
            tk.Label(latest_label, text="LATEST STORIES", font=F["btn"], fg=C["text_primary"],
                     bg=C["bg"]).pack(side="left")
            tk.Label(latest_label, text="YOUR LIVE FEED", font=F["meta"], fg=C["text_seen"],
                     bg=C["bg"]).pack(side="left", padx=10)
            grid = tk.Frame(self._sf.inner, bg=C["bg"])
            grid.pack(fill="both", expand=True)
            grid.grid_columnconfigure(0, weight=1, uniform="signal")
            grid.grid_columnconfigure(1, weight=1, uniform="signal")
            for index, item in enumerate(remaining):
                card = NewsCard(grid, item, on_click=self._open_item,
                                 on_context=self._show_card_menu, load_images=load_img)
                card.set_store(self.store)
                row, col = divmod(index, 2)
                card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
                self._cards.append(card)

        total  = len(items)
        unseen = sum(1 for i in items if not i.get("seen"))
        self._update_insight_panel(items)
        self._hdr_count.configure(
            text=t("unread_of", unread=unseen, total=total) if unseen
            else t("n_articles", n=total))

    def _open_item(self, item):
        self._focused_item = item
        self.store.mark_seen(item["id"]); item["seen"] = 1
        for c in self._cards:
            if hasattr(c,"item") and c.item.get("id")==item["id"]:
                if hasattr(c,"mark_seen"): c.mark_seen()
                break
        DetailWindow(self.root, item, store=self.store,
                     prefer_internal_video=self._settings.get("video_internal", False),
                     external_player_path=self._settings.get("external_player_path", ""))
        unseen = sum(1 for c in self._cards
                     if hasattr(c,"item") and not c.item.get("seen"))
        self._hdr_count.configure(
            text=t("unread_of", unread=unseen, total=len(self._cards)) if unseen
            else t("n_articles", n=len(self._cards)))

    def _show_card_menu(self, event, item):
        self._focused_item = item
        menu = tk.Menu(self.root, tearoff=0, bg=C["card"], fg=C["text_primary"],
                       activebackground=C["accent"], activeforeground="white")
        is_bookmarked = bool(item.get("bookmarked"))
        menu.add_command(label=t("bookmark_remove") if is_bookmarked else t("bookmark_add"),
                         command=lambda: self._toggle_item_bookmark(item))
        menu.add_command(label=t("copy_link"), command=lambda: self._copy_link(item.get("link", "")))
        menu.add_command(label=t("open_link"), command=lambda: webbrowser.open(item.get("link", "")))
        menu.add_command(label=t("reader_mode"), command=lambda: ReaderWindow(self.root, item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_link(self, url):
        if not url:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self._set_status(t("copy_link"))

    def _toggle_item_bookmark(self, item):
        new_state = self.store.toggle_bookmark(item["id"])
        item["bookmarked"] = int(new_state)
        self._reload()

    def _keyboard_shortcut(self, event):
        if isinstance(event.widget, (tk.Entry, tk.Text)):
            return
        key = event.keysym.lower()
        if key == "space" and self._sf:
            self._sf.canvas.yview_scroll(6, "units")
            return "break"
        if key == "b" and self._focused_item:
            self._toggle_item_bookmark(self._focused_item)
            return "break"
        if key == "o" and self._focused_item:
            webbrowser.open(self._focused_item.get("link", ""))
            return "break"

    def _toggle_auto_scroll(self):
        self._settings["auto_scroll"] = self._auto_scroll_var.get()
        config.save_settings(self._settings)
        if self._auto_scroll_var.get():
            self._schedule_auto_scroll()
        self._set_status(t("auto_scroll"))

    def _schedule_auto_scroll(self):
        if self._auto_scroll_job is not None:
            return
        def tick():
            self._auto_scroll_job = None
            if not getattr(self, "_auto_scroll_var", tk.BooleanVar(value=False)).get() or not self._sf:
                return
            speed = max(1, int(self._settings.get("auto_scroll_speed", 2)))
            self._sf.canvas.yview_scroll(speed, "units")
            self._auto_scroll_job = self.root.after(850, tick)
        self._auto_scroll_job = self.root.after(850, tick)

    def _switch_view(self):
        self._view_mode = self._view_var.get()
        self._reload()

    # ── Feed mgmt ──
    def _add_feed(self):
        url = simpledialog.askstring(t("add_feed_title"), t("add_feed_prompt"),
                                      parent=self.root)
        if url and url.strip():
            url = url.strip()
            category = simpledialog.askstring(t("category_title"), t("category_prompt"),
                                              parent=self.root) or "عمومی"
            self.store.add_feed(url, category=category)
            # track in settings so it survives restart
            added = self._settings.setdefault("added_feeds", [])
            deleted = self._settings.setdefault("deleted_feeds", [])
            if url not in added: added.append(url)
            if url in deleted:   deleted.remove(url)
            config.save_settings(self._settings)
            self._refresh_sidebar()
            self._select_feed(url)

    def _del_feed(self, url):
        if messagebox.askyesno(t("del_feed_title"), t("del_feed_confirm",url=url),
                                parent=self.root):
            self.store.remove_feed(url)
            # remember deletion so it won't be re-added on next start
            deleted = self._settings.setdefault("deleted_feeds", [])
            added   = self._settings.setdefault("added_feeds", [])
            if url not in deleted: deleted.append(url)
            if url in added:       added.remove(url)
            config.save_settings(self._settings)
            if self._active_feed == url: self._active_feed = None
            self._refresh_sidebar(); self._reload()

    def _toggle_pin(self, url, pinned):
        self.store.pin_feed(url, not pinned); self._refresh_sidebar()

    def _mark_all_read(self):
        feed = None if self._active_feed == "__bookmarks__" else self._active_feed
        count = self.store.mark_all_seen(feed)
        self._refresh_sidebar()
        self._reload()
        self._set_status(t("marked_all_read", n=count))

    def _import_opml(self):
        path = filedialog.askopenfilename(parent=self, title=t("import_opml"),
                                          filetypes=[("OPML", "*.opml *.xml"), ("All files", "*.*")])
        if not path:
            return
        try:
            count = self.store.import_opml(path)
            self._refresh_sidebar()
            self._set_status(t("import_done", n=count))
        except Exception as exc:
            messagebox.showerror(t("import_opml"), str(exc), parent=self.root)

    def _export_opml(self):
        path = filedialog.asksaveasfilename(parent=self, title=t("export_opml"),
                                            defaultextension=".opml",
                                            filetypes=[("OPML", "*.opml")])
        if not path:
            return
        try:
            self.store.export_opml(path, "RSS Reader Pro")
            self._set_status(t("export_done"))
        except Exception as exc:
            messagebox.showerror(t("export_opml"), str(exc), parent=self.root)

    def _export_bookmarks(self):
        path = filedialog.asksaveasfilename(parent=self, title=t("export_bookmarks"),
                                            defaultextension=".html",
                                            filetypes=[("HTML", "*.html"), ("PDF", "*.pdf")])
        if not path:
            return
        try:
            if path.lower().endswith(".pdf"):
                self.store.export_bookmarks_pdf(path)
            else:
                self.store.export_bookmarks_html(path)
            self._set_status(t("export_done"))
        except Exception as exc:
            messagebox.showerror(t("export_bookmarks"), str(exc), parent=self.root)

    def _check_all(self):
        self._set_status(t("checking_all"))
        def worker():
            for f in self.store.get_feeds():
                self._fetch_feed_data(f["url"], f.get("title") or f["url"], notify=True)
                time.sleep(0.3)
            self.root.after(0, self._refresh_sidebar)
            self.root.after(0, self._reload)
            self.root.after(0, lambda: self._set_status(t("checked_all")))
        threading.Thread(target=worker, daemon=True).start()

    def _fetch_feed_data(self, url, feed_title, notify=False):
        items = core.fetch_feed(url)
        new_items = [item for item in items if self.store.upsert(item, url)]
        if notify and self._settings.get("notifications", True) and new_items:
            core.notify_new_items(feed_title, new_items)
        return items, new_items

    def _fetch_feed(self, url):
        feed = next((f for f in self.store.get_feeds() if f["url"] == url), {})
        items, _ = self._fetch_feed_data(url, feed.get("title") or url, notify=True)
        self.root.after(0, self._refresh_sidebar)
        self.root.after(0, self._reload)
        self.root.after(0, lambda: self._set_status(t("fetched", n=len(items), url=url)))

    # ── DNS ──
    def _show_bookmarks(self):
        """Switch main view to bookmarks."""
        self._active_feed = "__bookmarks__"
        self._hdr_title.configure(text=t("bookmarks"))
        self._refresh_sidebar()
        self._reload()

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
        deleted  = set(self._settings.get("deleted_feeds", []))
        added    = self._settings.get("added_feeds", [])

        # Add default feeds — but skip ones the user explicitly deleted
        for feed in config.DEFAULT_FEEDS:
            if isinstance(feed, tuple):
                url, title, category = feed
            else:
                url, title, category = feed, "", "عمومی"
            if url not in existing and url not in deleted:
                self.store.add_feed(url, title, category)

        # Re-add user-added feeds that may have been lost
        for url in added:
            if url not in existing and url not in deleted:
                self.store.add_feed(url)

        self._refresh_sidebar()
        threading.Thread(target=self._initial_load, daemon=True).start()
        if config.CHECK_INTERVAL > 0:
            def auto():
                while True:
                    time.sleep(config.CHECK_INTERVAL)
                    for f in self.store.get_feeds():
                        self._fetch_feed_data(f["url"], f.get("title") or f["url"], notify=True)
                    self.root.after(0, self._refresh_sidebar)
                    self.root.after(0, self._reload)
            threading.Thread(target=auto, daemon=True).start()

    def _initial_load(self):
        self.root.after(0, lambda: self._set_status("Fetching feeds..."))
        for f in self.store.get_feeds():
            self._fetch_feed_data(f["url"], f.get("title") or f["url"], notify=False)
        self.root.after(0, self._reload)
        self.root.after(0, lambda: self._set_status(t("ready")))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("980x700")
    root.minsize(740, 520)
    RSSApp(root)
    root.mainloop()
