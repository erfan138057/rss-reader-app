"""Qt-based modern UI for RSS Reader Pro.

This module replaces the Tkinter presentation layer while keeping core.py as the
single source of truth for feeds, persistence, imports/exports, networking and media.
"""
from __future__ import annotations

import os
import sys
import time
import threading
import webbrowser
import subprocess
from functools import partial
from urllib.parse import urlparse

import httpx
from PySide6.QtCore import Qt, QSize, QTimer, Signal, QObject, QRunnable, QThreadPool, QDate
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QPen, QPixmap, QAction, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QToolButton,
    QLineEdit, QScrollArea, QVBoxLayout, QHBoxLayout, QGridLayout, QDialog,
    QTextBrowser, QTextEdit, QCheckBox, QComboBox, QDateEdit, QFormLayout,
    QDialogButtonBox, QInputDialog, QFileDialog, QMessageBox, QMenu,
    QSizePolicy, QSpacerItem
)

import config
import core
from i18n import t, set_lang

# ---------------------------------------------------------------------------
# Design system
# ---------------------------------------------------------------------------
C = {
    "canvas": "#0B1320", "sidebar": "#0D1826", "surface": "#14243A",
    "surface2": "#1A2E48", "card": "#182B45", "card_seen": "#121F31",
    "line": "#28415F", "text": "#F3F7FC", "muted": "#91A7C0",
    "dim": "#647B96", "teal": "#35D6C7", "teal_dark": "#1FAFA5",
    "coral": "#FF6B64", "amber": "#F8C94A", "success": "#42D392",
}

APP_QSS = f"""
QMainWindow, QDialog {{ background: {C['canvas']}; color: {C['text']}; font-family: 'Segoe UI', Arial; }}
QWidget {{ color: {C['text']}; font-family: 'Segoe UI', Arial; }}
QFrame#sidebar {{ background: {C['sidebar']}; border-right: 1px solid {C['line']}; }}
QFrame#insight {{ background: {C['surface']}; border: 1px solid {C['line']}; border-radius: 10px; }}
QFrame#topBar {{ background: {C['canvas']}; border-bottom: 1px solid {C['line']}; }}
QFrame#searchBar {{ background: {C['surface']}; border: 1px solid {C['line']}; border-radius: 10px; }}
QLineEdit {{ background: transparent; border: 0; color: {C['text']}; padding: 8px; selection-background-color: {C['teal_dark']}; }}
QLineEdit#dateEdit, QTextEdit {{ background: {C['surface2']}; border: 1px solid {C['line']}; border-radius: 7px; padding: 7px; }}
QPushButton {{ background: transparent; border: 0; border-radius: 7px; color: {C['muted']}; padding: 8px 10px; font-weight: 600; }}
QPushButton:hover {{ background: {C['surface2']}; color: {C['text']}; }}
QPushButton#primary {{ background: {C['teal']}; color: #06202A; }}
QPushButton#primary:hover {{ background: #5BE5D8; }}
QPushButton#darkButton {{ background: {C['surface2']}; color: {C['text']}; }}
QPushButton#activePill {{ background: {C['teal']}; color: #052127; border-radius: 7px; }}
QPushButton#pill {{ background: {C['surface2']}; color: {C['muted']}; border-radius: 7px; }}
QPushButton#pill:hover {{ color: {C['text']}; background: #23415F; }}
QPushButton#feed {{ text-align: left; border-radius: 7px; padding: 8px; }}
QPushButton#feed:checked {{ background: #1B4858; color: {C['text']}; border-left: 3px solid {C['teal']}; }}
QPushButton#moreTool {{ background: {C['surface2']}; color: {C['muted']}; }}
QScrollArea {{ border: 0; background: {C['canvas']}; }}
QWidget#content, QWidget#feedHost {{ background: {C['canvas']}; }}
QScrollBar:vertical {{ background: {C['canvas']}; width: 8px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: #29415F; border-radius: 4px; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QMenu {{ background: {C['surface']}; color: {C['text']}; border: 1px solid {C['line']}; padding: 5px; }}
QMenu::item {{ padding: 8px 22px 8px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {C['teal']}; color: #06202A; }}
QComboBox {{ background: {C['surface2']}; border: 1px solid {C['line']}; border-radius: 7px; padding: 6px 9px; color: {C['text']}; }}
QComboBox QAbstractItemView {{ background: {C['surface']}; color: {C['text']}; selection-background-color: {C['teal']}; }}
QCheckBox {{ color: {C['muted']}; spacing: 7px; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {C['line']}; border-radius: 4px; background: {C['surface2']}; }}
QCheckBox::indicator:checked {{ background: {C['teal']}; border-color: {C['teal']}; }}
QDateEdit {{ background: {C['surface2']}; border: 1px solid {C['line']}; border-radius: 7px; padding: 5px; color: {C['text']}; }}
QTextBrowser {{ background: {C['surface']}; border: 0; padding: 14px; color: {C['text']}; }}
"""


def label(text: str, size: int = 11, color: str | None = None, bold: bool = False) -> QLabel:
    w = QLabel(text)
    f = QFont("Segoe UI", size)
    f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color: {color or C['text']}; background: transparent;")
    return w


def button(text: str, object_name: str = "", checkable: bool = False) -> QPushButton:
    w = QPushButton(text)
    if object_name:
        w.setObjectName(object_name)
    w.setCheckable(checkable)
    w.setCursor(Qt.PointingHandCursor)
    return w


def open_system_video(url: str, external_player_path: str = ""):
    """Open a video using the user's chosen player or registered system handler."""
    try:
        if external_player_path and os.path.isfile(external_player_path):
            subprocess.Popen([external_player_path, url])
            core.LOG.info(f"Custom video player: {external_player_path}")
        elif sys.platform.startswith("win"):
            os.startfile(url)
            core.LOG.info(f"Windows default video handler: {url}")
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception as exc:
        core.LOG.error(f"System video handler failed: {exc}")
        webbrowser.open(url)


class Bridge(QObject):
    refreshed = Signal(str)
    loaded = Signal()
    network = Signal(dict)


class ImageSignals(QObject):
    done = Signal(bytes)


class ResultSignals(QObject):
    done = Signal(object)
    failed = Signal(str)


class ImageJob(QRunnable):
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.signals = ImageSignals()

    def run(self):
        data = b""
        try:
            response = httpx.get(self.url, timeout=10, follow_redirects=True,
                                 headers={"User-Agent": "RSSReaderPro/1.0"})
            if response.is_success:
                data = response.content
        except Exception:
            pass
        self.signals.done.emit(data)


class Pulse(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.setFixedSize(104, 104)

    def set_value(self, value: int):
        self.value = value
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(13, 13, -13, -13)
        p.setPen(QPen(QColor(C["line"]), 9, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(r)
        p.setPen(QPen(QColor(C["teal"]), 9, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(r, 90 * 16, -252 * 16)
        p.setPen(QColor(C["text"]))
        p.setFont(QFont("Segoe UI", 18, QFont.Bold))
        p.drawText(self.rect().adjusted(0, -7, 0, 0), Qt.AlignCenter, str(self.value))
        p.setPen(QColor(C["muted"]))
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(self.rect().adjusted(0, 27, 0, 0), Qt.AlignCenter, "UNREAD")


class ImageLabel(QLabel):
    def __init__(self, width: int, height: int, parent=None):
        super().__init__(parent)
        self.target_size = QSize(width, height)
        self.setMinimumHeight(height)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "border-radius: 8px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1, "
            "stop:0 #254365, stop:1 #15243A); color: #7E9AB7; font-weight: 700;"
        )
        self.setText("IMAGE")

    def load(self, url: str):
        if not url:
            return
        job = ImageJob(url)
        job.signals.done.connect(self.set_image)
        QThreadPool.globalInstance().start(job)

    def set_image(self, data: bytes):
        pixmap = QPixmap()
        if data and pixmap.loadFromData(data):
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            self.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)


class ArticleCard(QFrame):
    opened = Signal(dict)
    menu_requested = Signal(dict, object)

    def __init__(self, item: dict, featured: bool = False, parent=None):
        super().__init__(parent)
        self.item = item
        self.featured = featured
        self.setObjectName("articleCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#articleCard {{ background: {C['card_seen'] if item.get('seen') else C['card']};
                                border: 1px solid {C['line']}; border-radius: 10px; }}
            QFrame#articleCard:hover {{ background: #203B5A; border-color: {C['teal']}; }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(9)
        image_h = 130 if self.featured else 105
        self.image = ImageLabel(200, image_h)
        self.image.setFixedHeight(image_h)
        layout.addWidget(self.image)
        image_url = self.item.get("image_url") or ""
        self.image.load(image_url)

        top = QHBoxLayout()
        domain = urlparse(self.item.get("feed", "")).netloc.upper() or "RSS READER"
        status = "BREAKING NEWS" if self.featured and not self.item.get("seen") else domain[:24]
        status_color = C["coral"] if self.featured and not self.item.get("seen") else C["teal"]
        top.addWidget(label(status, 8, status_color, True))
        top.addStretch(1)
        if self.item.get("video_url"):
            top.addWidget(label("PLAY", 8, C["amber"], True))
        layout.addLayout(top)

        title = label(self.item.get("title") or "Untitled", 12 if self.featured else 11, C["text"], True)
        title.setWordWrap(True)
        title.setMaximumHeight(64)
        layout.addWidget(title)
        summary = (self.item.get("summary") or "").strip()
        if summary:
            excerpt = summary[:105] + ("…" if len(summary) > 105 else "")
            text = label(excerpt, 9, C["muted"])
            text.setWordWrap(True)
            text.setMaximumHeight(47)
            layout.addWidget(text)
        layout.addStretch(1)

        foot = QHBoxLayout()
        date = (self.item.get("published") or "")[:16].replace("T", " · ")
        foot.addWidget(label(date, 8, C["dim"]))
        foot.addStretch(1)
        self.bookmark = button("▮" if self.item.get("bookmarked") else "▯")
        self.bookmark.setStyleSheet(f"color: {C['amber'] if self.item.get('bookmarked') else C['dim']}; padding: 0;")
        self.bookmark.clicked.connect(self.toggle_bookmark)
        foot.addWidget(self.bookmark)
        layout.addLayout(foot)

    def toggle_bookmark(self):
        new_state = self.window().store.toggle_bookmark(self.item["id"])
        self.item["bookmarked"] = int(new_state)
        self.bookmark.setText("▮" if new_state else "▯")
        self.bookmark.setStyleSheet(f"color: {C['amber'] if new_state else C['dim']}; padding: 0;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.opened.emit(self.item)
        elif event.button() == Qt.RightButton:
            self.menu_requested.emit(self.item, event.globalPosition().toPoint())
        super().mousePressEvent(event)


class DetailDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle(item.get("title") or "Article")
        self.resize(760, 620)
        layout = QVBoxLayout(self)
        title = label(item.get("title") or "Untitled", 18, C["text"], True)
        title.setWordWrap(True)
        layout.addWidget(title)
        meta = f"{(item.get('published') or '')[:16]}   ·   {urlparse(item.get('feed', '')).netloc}"
        layout.addWidget(label(meta, 9, C["muted"]))
        view = QTextBrowser()
        summary = item.get("summary") or ""
        view.setHtml(f"<h3 style='color:{C['teal']}'>Summary</h3><p>{summary}</p><p style='color:{C['muted']}'>Open Reader Mode for a clean version of the full article.</p>")
        layout.addWidget(view, 1)
        bar = QHBoxLayout()
        reader = button("Reader mode", "darkButton")
        reader.clicked.connect(self.open_reader)
        bar.addWidget(reader)
        open_btn = button("Open article", "primary")
        open_btn.clicked.connect(lambda: webbrowser.open(self.item.get("link", "")))
        bar.addWidget(open_btn)
        if self.item.get("video_url"):
            vid = button("Play video", "darkButton")
            player_path = getattr(parent, "settings", {}).get("external_player_path", "") if parent else ""
            vid.clicked.connect(lambda: open_system_video(self.item.get("video_url"), player_path))
            bar.addWidget(vid)
        bar.addStretch(1)
        close = button("Close")
        close.clicked.connect(self.accept)
        bar.addWidget(close)
        layout.addLayout(bar)

    def open_reader(self):
        dlg = ReaderDialog(self.item, self)
        dlg.exec()


class ReaderDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Reader Mode")
        self.resize(760, 700)
        layout = QVBoxLayout(self)
        self.title = label(item.get("title") or "Reader Mode", 17, C["text"], True)
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.body = QTextBrowser()
        self.body.setText("Loading clean article…")
        self.reader_signals = ResultSignals(self)
        self.reader_signals.done.connect(self.apply_reader)
        self.reader_signals.failed.connect(lambda message: self.body.setText(f"Reader Mode could not load this article.\n\n{message}"))
        layout.addWidget(self.body, 1)
        close = button("Close", "darkButton")
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=Qt.AlignRight)
        threading.Thread(target=self.load_reader, daemon=True).start()

    def load_reader(self):
        try:
            self.reader_signals.done.emit(core.fetch_reader_content(self.item.get("link", "")))
        except Exception as exc:
            self.reader_signals.failed.emit(str(exc))

    def apply_reader(self, result: dict):
        self.title.setText(result.get("title") or self.item.get("title") or "Reader Mode")
        self.body.setPlainText(result.get("text") or "")


class FilterDialog(QDialog):
    def __init__(self, state: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced filters")
        self.resize(380, 260)
        layout = QVBoxLayout(self)
        self.unread = QCheckBox("Unread only")
        self.unread.setChecked(state.get("unread", False))
        self.bookmarked = QCheckBox("Bookmarks only")
        self.bookmarked.setChecked(state.get("bookmarked", False))
        layout.addWidget(self.unread); layout.addWidget(self.bookmarked)
        form = QFormLayout()
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.from_date.setSpecialValueText("Any date")
        self.to_date.setSpecialValueText("Any date")
        self.from_date.setDate(QDate.fromString(state.get("from", ""), "yyyy-MM-dd") if state.get("from") else QDate(2000, 1, 1))
        self.to_date.setDate(QDate.fromString(state.get("to", ""), "yyyy-MM-dd") if state.get("to") else QDate.currentDate())
        form.addRow("From", self.from_date); form.addRow("To", self.to_date)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> dict:
        return {"unread": self.unread.isChecked(), "bookmarked": self.bookmarked.isChecked(),
                "from": self.from_date.date().toString("yyyy-MM-dd"),
                "to": self.to_date.date().toString("yyyy-MM-dd")}


class SettingsDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(420, 330)
        self.settings = dict(settings)
        form = QFormLayout(self)
        self.language = QComboBox(); self.language.addItems(["English", "فارسی"])
        self.language.setCurrentIndex(1 if settings.get("language") == "fa" else 0)
        self.theme = QComboBox(); self.theme.addItems(["Dark", "Light"])
        self.theme.setCurrentIndex(1 if settings.get("theme") == "light" else 0)
        self.font_size = QComboBox(); self.font_size.addItems([str(v) for v in range(8, 17)])
        self.font_size.setCurrentText(str(settings.get("font_size", 9)))
        self.images = QCheckBox("Load article images"); self.images.setChecked(settings.get("load_images", True))
        self.notifications = QCheckBox("Notify when new articles arrive"); self.notifications.setChecked(settings.get("notifications", True))
        self.player = QLineEdit(settings.get("external_player_path", "")); self.player.setPlaceholderText("Optional custom media-player path")
        form.addRow("Language", self.language); form.addRow("Theme", self.theme); form.addRow("Font size", self.font_size)
        form.addRow(self.images); form.addRow(self.notifications); form.addRow("Player", self.player)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def value(self) -> dict:
        out = dict(self.settings)
        out.update({"language": "fa" if self.language.currentIndex() else "en", "theme": "light" if self.theme.currentIndex() else "dark",
                    "font_size": int(self.font_size.currentText()), "load_images": self.images.isChecked(),
                    "notifications": self.notifications.isChecked(), "external_player_path": self.player.text().strip()})
        return out


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = config.load_settings()
        set_lang(self.settings.get("language", "en"))
        self.store = core.Store(config.DB_FILE)
        self.bridge = Bridge()
        self.bridge.refreshed.connect(self.on_refreshed)
        self.bridge.loaded.connect(self.on_loaded)
        self.bridge.network.connect(self.on_network)
        self.pool = QThreadPool.globalInstance()
        self.active_feed: str | None = None
        self.focused_item: dict | None = None
        self.filters = {"unread": False, "bookmarked": False, "from": "", "to": ""}
        self.sort = self.settings.get("sort", "newest")
        self.show_read = self.settings.get("show_read", True)
        self.auto_scroll = self.settings.get("auto_scroll", False)
        self.setWindowTitle("RSS Reader Pro")
        self.setMinimumSize(1240, 760)
        self.resize(1520, 920)
        self.build_ui()
        self.install_shortcuts()
        self.monitor = core.InternetMonitor(interval=45, on_update=lambda value: self.bridge.network.emit(value))
        self.monitor.start()
        self.install_default_feeds()
        self.refresh_all()
        self.fetch_initial_async()
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.auto_scroll_tick)
        if self.auto_scroll:
            self.scroll_timer.start(850)

    def build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.sidebar = self.make_sidebar()
        layout.addWidget(self.sidebar)
        self.main = QWidget(); main_layout = QVBoxLayout(self.main); main_layout.setContentsMargins(22, 18, 22, 10); main_layout.setSpacing(12)
        main_layout.addWidget(self.make_header())
        main_layout.addWidget(self.make_search())
        main_layout.addWidget(self.make_toolbar())
        workspace = QHBoxLayout(); workspace.setSpacing(14)
        self.content_scroll = QScrollArea(); self.content_scroll.setWidgetResizable(True); self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_scroll.viewport().setStyleSheet(f"background: {C['canvas']};")
        self.content = QWidget(); self.content.setObjectName("content")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(15)
        self.content_scroll.setWidget(self.content)
        workspace.addWidget(self.content_scroll, 1)
        self.insight = self.make_insight(); workspace.addWidget(self.insight)
        main_layout.addLayout(workspace, 1)
        main_layout.addWidget(self.make_status())
        layout.addWidget(self.main, 1)

    def make_sidebar(self):
        panel = QFrame(); panel.setObjectName("sidebar"); panel.setFixedWidth(236)
        layout = QVBoxLayout(panel); layout.setContentsMargins(14, 18, 14, 12); layout.setSpacing(9)
        brand = QHBoxLayout(); mark = label("⌁", 26, C["teal"], True); brand.addWidget(mark)
        names = QVBoxLayout(); names.addWidget(label("RSS Reader", 15, C["text"], True)); names.addWidget(label("YOUR DAILY SIGNAL", 8, C["dim"], True)); brand.addLayout(names); brand.addStretch(1)
        theme = button("◐"); theme.clicked.connect(self.toggle_theme); brand.addWidget(theme)
        layout.addLayout(brand); layout.addSpacing(10)
        self.all_btn = button("◉  All feeds", "feed", True); self.all_btn.clicked.connect(lambda: self.select_feed(None)); layout.addWidget(self.all_btn)
        self.bookmarks_btn = button("▣  Bookmarks", "feed", True); self.bookmarks_btn.clicked.connect(self.show_bookmarks); layout.addWidget(self.bookmarks_btn)
        quick = QHBoxLayout(); add = button("＋ Add feed", "primary"); add.clicked.connect(self.add_feed); quick.addWidget(add)
        refresh = button("↻", "darkButton"); refresh.setFixedWidth(38); refresh.clicked.connect(self.fetch_all_async); quick.addWidget(refresh)
        settings = button("⚙", "darkButton"); settings.setFixedWidth(38); settings.clicked.connect(self.open_settings); quick.addWidget(settings)
        layout.addLayout(quick); layout.addSpacing(8); layout.addWidget(label("FEED COLLECTIONS", 8, C["dim"], True))
        self.feed_scroll = QScrollArea(); self.feed_scroll.setWidgetResizable(True); self.feed_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.feed_scroll.viewport().setStyleSheet(f"background: {C['sidebar']};")
        self.feed_host = QWidget(); self.feed_host.setObjectName("feedHost"); self.feed_host.setStyleSheet(f"background: {C['sidebar']};")
        self.feed_layout = QVBoxLayout(self.feed_host); self.feed_layout.setContentsMargins(0, 0, 0, 0); self.feed_layout.setSpacing(3); self.feed_layout.addStretch(1)
        self.feed_scroll.setWidget(self.feed_host); layout.addWidget(self.feed_scroll, 1)
        more = button("⋯  More tools", "moreTool"); more.clicked.connect(self.more_tools); layout.addWidget(more)
        net = QFrame(); net.setStyleSheet(f"background:{C['surface']}; border:1px solid {C['line']}; border-radius:8px;")
        nl = QVBoxLayout(net); nl.setContentsMargins(10, 8, 10, 8); nl.addWidget(label(f"DNS · {config.ACTIVE_DOH['name']}", 8, C["muted"])); self.side_network = label("● Checking…", 8, C["success"]); nl.addWidget(self.side_network)
        layout.addWidget(net)
        return panel

    def make_header(self):
        header = QFrame(); header.setObjectName("topBar"); layout = QHBoxLayout(header); layout.setContentsMargins(0, 0, 0, 10)
        box = QVBoxLayout(); self.heading = label("All News", 18, C["text"], True); self.subheading = label("", 9, C["muted"]); box.addWidget(self.heading); box.addWidget(self.subheading); layout.addLayout(box); layout.addStretch(1)
        self.auto_btn = button("□  Auto-scroll", "darkButton", True); self.auto_btn.clicked.connect(self.toggle_auto); layout.addWidget(self.auto_btn)
        mark = button("✓  Mark all as read", "darkButton"); mark.clicked.connect(self.mark_all_read); layout.addWidget(mark)
        return header

    def make_search(self):
        bar = QFrame(); bar.setObjectName("searchBar"); row = QHBoxLayout(bar); row.setContentsMargins(12, 3, 8, 3); row.addWidget(label("⌕", 18, C["muted"]))
        self.search = QLineEdit(); self.search.setPlaceholderText("Search stories, sources and topics"); self.search.textChanged.connect(self.refresh_view); row.addWidget(self.search, 1)
        filters = button("Filters", "darkButton"); filters.clicked.connect(self.open_filters); row.addWidget(filters)
        return bar

    def make_toolbar(self):
        bar = QWidget(); row = QHBoxLayout(bar); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(7)
        self.all_stories = button("All stories", "activePill"); self.all_stories.clicked.connect(lambda: self.set_mode("all")); row.addWidget(self.all_stories)
        self.timeline = button("Timeline", "pill"); self.timeline.clicked.connect(lambda: self.set_mode("timeline")); row.addWidget(self.timeline)
        self.show_read_btn = button("✓  Show read"); self.show_read_btn.setCheckable(True); self.show_read_btn.setChecked(self.show_read); self.show_read_btn.clicked.connect(self.toggle_show_read); row.addWidget(self.show_read_btn)
        row.addStretch(1); row.addWidget(label("SORT", 8, C["dim"], True))
        self.sort_btn = button("Newest  ▾", "darkButton"); self.sort_btn.clicked.connect(self.sort_menu); row.addWidget(self.sort_btn)
        return bar

    def make_insight(self):
        panel = QFrame(); panel.setObjectName("insight"); panel.setFixedWidth(205); layout = QVBoxLayout(panel); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(6)
        layout.addWidget(label("SIGNAL", 10, C["text"], True)); layout.addWidget(label("YOUR READING PULSE", 8, C["dim"], True)); self.pulse = Pulse(); layout.addWidget(self.pulse, alignment=Qt.AlignHCenter)
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background:{C['line']};"); layout.addWidget(line); layout.addWidget(label("TOPICS", 8, C["dim"], True))
        for name in ("World", "Technology", "Business", "Culture"):
            chip = label(name, 9, C["muted"]); chip.setAlignment(Qt.AlignCenter); chip.setStyleSheet(f"background:{C['surface2']}; color:{C['muted']}; border-radius:6px; padding:7px;"); layout.addWidget(chip)
        line2 = QFrame(); line2.setFixedHeight(1); line2.setStyleSheet(f"background:{C['line']};"); layout.addWidget(line2); layout.addWidget(label("TIP", 8, C["dim"], True)); tip = label("Save stories to build your reading queue.", 9, C["muted"]); tip.setWordWrap(True); layout.addWidget(tip); layout.addStretch(1)
        return panel

    def make_status(self):
        bar = QFrame(); bar.setStyleSheet(f"background:{C['sidebar']}; border-top:1px solid {C['line']};")
        row = QHBoxLayout(bar); row.setContentsMargins(12, 6, 12, 6); self.status = label("● Ready", 8, C["muted"]); self.network = label("● Checking…", 8, C["success"]); row.addWidget(self.status); row.addStretch(1); row.addWidget(self.network)
        return bar

    # -- core-backed behavior -------------------------------------------------
    def install_default_feeds(self):
        known = {f["url"] for f in self.store.get_feeds()}; deleted = set(self.settings.get("deleted_feeds", []))
        for url, title, category in config.DEFAULT_FEEDS:
            if url not in known and url not in deleted:
                self.store.add_feed(url, title, category)

    def select_feed(self, url):
        self.active_feed = url
        self.heading.setText("All News" if url is None else urlparse(url).netloc)
        self.bookmarks_btn.setChecked(False); self.all_btn.setChecked(url is None)
        self.refresh_all(); self.refresh_view()
        if url:
            self.fetch_feed_async(url)

    def show_bookmarks(self):
        self.active_feed = "__bookmarks__"; self.heading.setText("Bookmarks"); self.bookmarks_btn.setChecked(True); self.all_btn.setChecked(False); self.refresh_all(); self.refresh_view()

    def refresh_all(self):
        self.refresh_sidebar(); self.refresh_view()

    def refresh_sidebar(self):
        while self.feed_layout.count():
            child = self.feed_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        counts = self.store.get_unread_counts(); grouped = {}
        for feed in self.store.get_feeds(): grouped.setdefault(feed.get("category") or "General", []).append(feed)
        for category, feeds in grouped.items():
            self.feed_layout.addWidget(label(category.upper(), 8, C["teal"], True))
            for feed in feeds:
                count = counts.get(feed["url"], 0); title = feed.get("title") or urlparse(feed["url"]).netloc
                name = ("●  " if feed.get("pinned") else "") + title + (f"   {count}" if count else "")
                item = button(name, "feed", True); item.setChecked(self.active_feed == feed["url"]); item.clicked.connect(partial(self.select_feed, feed["url"]))
                item.setContextMenuPolicy(Qt.CustomContextMenu); item.customContextMenuRequested.connect(partial(self.feed_menu, feed))
                self.feed_layout.addWidget(item)
        self.feed_layout.addStretch(1)

    def feed_menu(self, feed: dict, point):
        menu = QMenu(self); pin = menu.addAction("Unpin feed" if feed.get("pinned") else "Pin feed"); remove = menu.addAction("Remove feed")
        action = menu.exec(self.cursor().pos())
        if action == pin:
            self.store.pin_feed(feed["url"], not feed.get("pinned")); self.refresh_sidebar()
        elif action == remove:
            self.remove_feed(feed["url"])

    def refresh_view(self):
        query = self.search.text().strip() if hasattr(self, "search") else ""
        unread_only = self.filters.get("unread", False) or not self.show_read
        if self.active_feed == "__bookmarks__":
            items = self.store.search_items(query, None, self.sort, unread_only, True, self.filters.get("from", ""), self.filters.get("to", ""))
        else:
            items = self.store.search_items(query, self.active_feed, self.sort, unread_only, self.filters.get("bookmarked", False), self.filters.get("from", ""), self.filters.get("to", ""))
        unseen = sum(1 for item in items if not item.get("seen")); self.subheading.setText(f"{unseen} unread / {len(items)} stories"); self.pulse.set_value(unseen)
        outer = self.content_layout
        while outer.count():
            child = outer.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        if not items:
            empty = label("No stories found yet", 14, C["muted"]); empty.setAlignment(Qt.AlignCenter); outer.addWidget(empty); outer.addStretch(1); return
        section = QHBoxLayout(); section.addWidget(label("TOP STORIES", 11, C["text"], True)); section.addWidget(label("A QUICK VIEW OF WHAT MATTERS", 8, C["dim"], True)); section.addStretch(1); outer.addLayout(section)
        featured = QGridLayout(); featured.setSpacing(10)
        for idx, item in enumerate(items[:3]):
            card = ArticleCard(item, featured=True); card.opened.connect(self.open_item); card.menu_requested.connect(self.article_menu); featured.addWidget(card, 0, idx)
        outer.addLayout(featured)
        section2 = QHBoxLayout(); section2.addWidget(label("LATEST STORIES", 11, C["text"], True)); section2.addWidget(label("YOUR LIVE FEED", 8, C["dim"], True)); section2.addStretch(1); outer.addLayout(section2)
        grid = QGridLayout(); grid.setSpacing(10)
        remaining = items[3:] or items
        for idx, item in enumerate(remaining):
            card = ArticleCard(item, featured=False); card.opened.connect(self.open_item); card.menu_requested.connect(self.article_menu); grid.addWidget(card, idx // 3, idx % 3)
        outer.addLayout(grid); outer.addStretch(1)

    def open_item(self, item):
        self.focused_item = item; self.store.mark_seen(item["id"]); item["seen"] = 1; self.refresh_view(); DetailDialog(item, self).exec()

    def article_menu(self, item, pos):
        self.focused_item = item; menu = QMenu(self)
        bookmark = menu.addAction("Remove bookmark" if item.get("bookmarked") else "Bookmark")
        copy = menu.addAction("Copy link"); open_link = menu.addAction("Open in browser"); reader = menu.addAction("Reader mode")
        chosen = menu.exec(pos)
        if chosen == bookmark:
            self.store.toggle_bookmark(item["id"]); self.refresh_view()
        elif chosen == copy:
            QApplication.clipboard().setText(item.get("link", "")); self.set_status("Link copied")
        elif chosen == open_link:
            webbrowser.open(item.get("link", ""))
        elif chosen == reader:
            ReaderDialog(item, self).exec()

    def add_feed(self):
        url, ok = QInputDialog.getText(self, "Add feed", "RSS URL:")
        if not ok or not url.strip(): return
        title, _ = QInputDialog.getText(self, "Add feed", "Name (optional):")
        category, _ = QInputDialog.getText(self, "Feed category", "Category:", text="General")
        self.store.add_feed(url.strip(), title.strip(), category.strip() or "General")
        added = set(self.settings.get("added_feeds", [])); added.add(url.strip()); self.settings["added_feeds"] = sorted(added); config.save_settings(self.settings); self.refresh_all()

    def remove_feed(self, url):
        answer = QMessageBox.question(self, "Remove feed", "Remove this feed and its saved articles?", QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.store.remove_feed(url); deleted = set(self.settings.get("deleted_feeds", [])); deleted.add(url); self.settings["deleted_feeds"] = sorted(deleted); config.save_settings(self.settings); self.active_feed = None; self.refresh_all()

    def mark_all_read(self):
        count = self.store.mark_all_seen(None if self.active_feed in (None, "__bookmarks__") else self.active_feed); self.set_status(f"Marked {count} stories as read"); self.refresh_all()

    def toggle_show_read(self):
        self.show_read = self.show_read_btn.isChecked(); self.settings["show_read"] = self.show_read; config.save_settings(self.settings); self.refresh_view()

    def set_mode(self, mode):
        active = mode == "all"; self.all_stories.setObjectName("activePill" if active else "pill"); self.timeline.setObjectName("pill" if active else "activePill"); self.all_stories.style().unpolish(self.all_stories); self.all_stories.style().polish(self.all_stories); self.timeline.style().unpolish(self.timeline); self.timeline.style().polish(self.timeline)
        # Timeline retains the same data but changes ordering to oldest-first for scanning history.
        self.sort = "newest" if active else "oldest"; self.sort_btn.setText(("Newest" if active else "Oldest") + "  ▾"); self.refresh_view()

    def sort_menu(self):
        menu = QMenu(self)
        for text, value in [("Newest", "newest"), ("Oldest", "oldest"), ("Most popular", "popularity")]:
            action = menu.addAction(text); action.triggered.connect(partial(self.set_sort, value))
        menu.exec(self.sort_btn.mapToGlobal(self.sort_btn.rect().bottomLeft()))

    def set_sort(self, value):
        self.sort = value; names = {"newest": "Newest", "oldest": "Oldest", "popularity": "Most popular"}; self.sort_btn.setText(names[value] + "  ▾"); self.settings["sort"] = value; config.save_settings(self.settings); self.refresh_view()

    def open_filters(self):
        dlg = FilterDialog(self.filters, self)
        if dlg.exec(): self.filters = dlg.value(); self.refresh_view()

    def toggle_auto(self):
        self.auto_scroll = self.auto_btn.isChecked(); self.auto_btn.setText(("✓  " if self.auto_scroll else "□  ") + "Auto-scroll"); self.settings["auto_scroll"] = self.auto_scroll; config.save_settings(self.settings)
        if self.auto_scroll: self.scroll_timer.start(850)
        else: self.scroll_timer.stop()

    def auto_scroll_tick(self):
        bar = self.content_scroll.verticalScrollBar(); bar.setValue(bar.value() + int(self.settings.get("auto_scroll_speed", 2)) * 4)

    def more_tools(self):
        menu = QMenu(self)
        actions = [("Import OPML", self.import_opml), ("Export OPML", self.export_opml), ("Export bookmarks", self.export_bookmarks), ("DNS Scanner", self.open_dns), ("App log", self.open_log)]
        for name, fn in actions: menu.addAction(name, fn)
        menu.exec(self.cursor().pos())

    def import_opml(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import OPML", "", "OPML files (*.opml *.xml)")
        if path:
            try: self.set_status(f"Imported {self.store.import_opml(path)} feeds"); self.refresh_all()
            except Exception as exc: QMessageBox.warning(self, "Import OPML", str(exc))

    def export_opml(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export OPML", "rss-feeds.opml", "OPML files (*.opml)")
        if path:
            try: self.store.export_opml(path); self.set_status("OPML exported")
            except Exception as exc: QMessageBox.warning(self, "Export OPML", str(exc))

    def export_bookmarks(self):
        path, selected = QFileDialog.getSaveFileName(self, "Export bookmarks", "bookmarks.html", "HTML (*.html);;PDF (*.pdf)")
        if path:
            try:
                if path.lower().endswith(".pdf"): self.store.export_bookmarks_pdf(path)
                else:
                    if not path.lower().endswith(".html"): path += ".html"
                    self.store.export_bookmarks_html(path)
                self.set_status("Bookmarks exported")
            except Exception as exc: QMessageBox.warning(self, "Export bookmarks", str(exc))

    def open_dns(self):
        dlg = QDialog(self); dlg.setWindowTitle("DNS Scanner"); dlg.resize(500, 420); layout = QVBoxLayout(dlg); output = QTextEdit(); output.setReadOnly(True); layout.addWidget(output, 1)
        scan = button("Scan DNS providers", "primary"); layout.addWidget(scan)
        signals = ResultSignals(dlg)
        signals.done.connect(lambda lines: output.setPlainText("\n".join(lines)))
        signals.failed.connect(lambda message: output.setPlainText("Scan failed: " + message))
        def run():
            output.setText("Scanning DNS providers…")
            def worker():
                try:
                    results = core.DNSScanner().scan_all(config.DOH_SERVERS, config.FILTER_TEST_SITES)
                    signals.done.emit([f"{r['name']}: {'OK' if r['working'] else 'Unavailable'} · {r.get('latency_ms') or '-'}ms" for r in results])
                except Exception as exc:
                    signals.failed.emit(str(exc))
            threading.Thread(target=worker, daemon=True).start()
        scan.clicked.connect(run); dlg.exec()

    def open_log(self):
        dlg = QDialog(self); dlg.setWindowTitle("App log"); dlg.resize(760, 480); layout = QVBoxLayout(dlg); out = QTextEdit(); out.setReadOnly(True); out.setPlainText("\n".join(core.LOG.get_lines())); layout.addWidget(out); dlg.exec()

    def open_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self.settings = dlg.value(); config.save_settings(self.settings); set_lang(self.settings.get("language", "en")); QMessageBox.information(self, "Settings", "Restart the app to apply language and theme changes.")

    def toggle_theme(self):
        self.settings["theme"] = "light" if self.settings.get("theme") == "dark" else "dark"; config.save_settings(self.settings); QMessageBox.information(self, "Theme", "Restart the app to apply the selected theme.")

    def fetch_initial_async(self):
        def worker():
            for feed in self.store.get_feeds(): self.fetch_feed_data(feed["url"], feed.get("title") or feed["url"], False)
            self.bridge.loaded.emit()
        threading.Thread(target=worker, daemon=True).start()

    def fetch_all_async(self):
        def worker():
            for feed in self.store.get_feeds(): self.fetch_feed_data(feed["url"], feed.get("title") or feed["url"], True)
            self.bridge.loaded.emit()
        threading.Thread(target=worker, daemon=True).start()

    def fetch_feed_async(self, url):
        feed = next((f for f in self.store.get_feeds() if f["url"] == url), {})
        threading.Thread(target=lambda: (self.fetch_feed_data(url, feed.get("title") or url, True), self.bridge.loaded.emit()), daemon=True).start()

    def fetch_feed_data(self, url, title, notify):
        items = core.fetch_feed(url); fresh = [item for item in items if self.store.upsert(item, url)]
        if notify and self.settings.get("notifications", True) and fresh: core.notify_new_items(title, fresh)
        return fresh

    def on_loaded(self):
        self.refresh_all(); self.set_status("● Ready")

    def on_refreshed(self, message):
        self.refresh_all(); self.set_status(message)

    def on_network(self, result):
        self.network.setText("● " + result.get("label", "Checking…")); self.network.setStyleSheet(f"color:{result.get('color', C['success'])};")
        self.side_network.setText("● " + result.get("label", "Checking…")); self.side_network.setStyleSheet(f"color:{result.get('color', C['success'])};")

    def set_status(self, value):
        self.status.setText(value)

    def install_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, activated=lambda: self.content_scroll.verticalScrollBar().setValue(self.content_scroll.verticalScrollBar().value() + 220))
        QShortcut(QKeySequence("B"), self, activated=self.shortcut_bookmark)
        QShortcut(QKeySequence("O"), self, activated=lambda: webbrowser.open(self.focused_item.get("link", "")) if self.focused_item else None)

    def shortcut_bookmark(self):
        if self.focused_item:
            self.store.toggle_bookmark(self.focused_item["id"]); self.refresh_view()

    def closeEvent(self, event):
        self.monitor.stop(); event.accept()


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
