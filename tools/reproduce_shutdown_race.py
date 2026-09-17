"""Reproduce a UI shutdown racing a background feed fetch."""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

workspace = tempfile.TemporaryDirectory()
os.environ["XDG_DATA_HOME"] = workspace.name

import config
config.DB_FILE = str(Path(workspace.name) / "rss_reader.db")
config.SETTINGS_FILE = str(Path(workspace.name) / "settings.json")
config.DEFAULT_FEEDS = []

import core
import qt_gui
from PySide6.QtWidgets import QApplication


class QuietMonitor:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def stop(self):
        pass


def main():
    errors = []
    started = threading.Event()
    release = threading.Event()
    original_excepthook = threading.excepthook
    original_monitor = core.InternetMonitor
    original_initial = qt_gui.MainWindow.fetch_initial_async
    original_fetch = qt_gui.MainWindow.fetch_feed_data

    def record_exception(args):
        errors.append(f"{args.exc_type.__name__}: {args.exc_value}")

    def slow_fetch(self, _url, _title, _notify):
        started.set()
        release.wait(timeout=5)
        return []

    threading.excepthook = record_exception
    core.InternetMonitor = QuietMonitor
    qt_gui.MainWindow.fetch_initial_async = lambda _self: None
    qt_gui.MainWindow.fetch_feed_data = slow_fetch
    app = QApplication.instance() or QApplication(sys.argv)
    window = qt_gui.MainWindow()
    window.store.add_feed("https://news.example/rss", "News", "News")
    window.fetch_feed_async("https://news.example/rss")
    assert started.wait(timeout=2), "Background fetch did not start."
    window.close()
    window.deleteLater()
    for _ in range(8):
        app.processEvents()
    release.set()
    time.sleep(0.2)
    for _ in range(8):
        app.processEvents()

    threading.excepthook = original_excepthook
    core.InternetMonitor = original_monitor
    qt_gui.MainWindow.fetch_initial_async = original_initial
    qt_gui.MainWindow.fetch_feed_data = original_fetch
    assert not errors, "Background fetch must not emit through deleted UI objects: " + "; ".join(errors)


if __name__ == "__main__":
    main()
