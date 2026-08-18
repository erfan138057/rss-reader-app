"""Regression tests for the Qt interaction paths introduced in v1.0.3."""
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
import core
import qt_gui
from PySide6.QtWidgets import QApplication, QPushButton


class QuietMonitor:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class QtInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = config.DB_FILE
        self.original_settings = config.SETTINGS_FILE
        self.original_default_feeds = config.DEFAULT_FEEDS
        self.original_monitor = core.InternetMonitor
        self.original_fetch_initial = qt_gui.MainWindow.fetch_initial_async
        self.original_image_load = qt_gui.ImageLabel.load
        self.original_browser_open = qt_gui.webbrowser.open
        config.DB_FILE = os.path.join(self.temp_dir.name, "rss_reader.db")
        config.SETTINGS_FILE = os.path.join(self.temp_dir.name, "settings.json")
        config.DEFAULT_FEEDS = []
        core.InternetMonitor = QuietMonitor
        qt_gui.MainWindow.fetch_initial_async = lambda _self: None
        qt_gui.ImageLabel.load = lambda _self, _url, _article_url="": None
        self.browser_calls = []
        qt_gui.webbrowser.open = lambda url: self.browser_calls.append(url)
        self.window = qt_gui.MainWindow()
        self.window.store.add_feed("https://news.example/rss", "News", "News")
        self.window.store.upsert({
            "id": "article-1",
            "title": "Regression article",
            "link": "https://news.example/article",
            "summary": "Regression summary.",
            "published": "2026-08-18",
            "image_url": "",
            "video_url": "",
            "video_type": "",
        }, "https://news.example/rss")
        self.window.show()
        self.process_events()

    def tearDown(self):
        for dialog in [w for w in self.app.topLevelWidgets() if isinstance(w, qt_gui.VideoDialog)]:
            dialog.close()
        self.window.close()
        self.process_events()
        self.window.store.conn.close()
        config.DB_FILE = self.original_db
        config.SETTINGS_FILE = self.original_settings
        config.DEFAULT_FEEDS = self.original_default_feeds
        core.InternetMonitor = self.original_monitor
        qt_gui.MainWindow.fetch_initial_async = self.original_fetch_initial
        qt_gui.ImageLabel.load = self.original_image_load
        qt_gui.webbrowser.open = self.original_browser_open
        self.temp_dir.cleanup()

    def process_events(self):
        for _ in range(8):
            self.app.processEvents()

    def test_selecting_feed_keeps_cards_parented_and_opens_nothing(self):
        self.window.fetch_feed_async = lambda _url, notify=False: None
        before = set(self.app.topLevelWidgets())
        self.window.select_feed("https://news.example/rss")
        self.process_events()
        extra = [widget for widget in self.app.topLevelWidgets() if widget not in before and widget.isVisible()]
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.active_feed, "https://news.example/rss")
        self.assertFalse(extra)
        self.assertFalse(self.browser_calls)

    def test_close_suppresses_late_background_fetch_callback(self):
        started = threading.Event()
        release = threading.Event()
        failures = []
        original_hook = threading.excepthook

        def record_failure(args):
            failures.append(f"{args.exc_type.__name__}: {args.exc_value}")

        def slow_fetch(_url, _title, _notify):
            started.set()
            release.wait(timeout=3)
            return []

        threading.excepthook = record_failure
        self.window.fetch_feed_data = slow_fetch
        self.window.fetch_feed_async("https://news.example/rss")
        self.assertTrue(started.wait(timeout=2))
        self.window.close()
        self.window.deleteLater()
        self.process_events()
        release.set()
        time.sleep(0.2)
        self.process_events()
        threading.excepthook = original_hook
        self.assertFalse(failures, "A late worker callback must not access a deleted Qt signal source.")

    def test_direct_video_opens_native_in_app_player(self):
        item = {
            "title": "Direct media",
            "link": "https://news.example/video",
            "summary": "Direct media regression test.",
            "video_url": "https://media.w3.org/2010/05/sintel/trailer.mp4",
            "video_type": "direct",
        }
        detail = qt_gui.DetailDialog(item, self.window)
        play = next(button for button in detail.findChildren(QPushButton) if button.text() == qt_gui.t("play_video"))
        play.click()
        self.process_events()
        dialogs = [widget for widget in self.app.topLevelWidgets() if isinstance(widget, qt_gui.VideoDialog) and widget.isVisible()]
        self.assertEqual(len(dialogs), 1)
        self.assertEqual(dialogs[0].player.source().toString(), item["video_url"])
        self.assertFalse(self.browser_calls)
        detail.close()


if __name__ == "__main__":
    unittest.main()
