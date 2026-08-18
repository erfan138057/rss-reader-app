"""Headless behavioral checks for the Qt feed-selection and video paths."""
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sandbox = tempfile.TemporaryDirectory()
base = Path(sandbox.name)
os.environ["XDG_DATA_HOME"] = str(base)

import config
config.DB_FILE = str(base / "rss_reader.db")
config.SETTINGS_FILE = str(base / "settings.json")
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


def process_events(app, cycles=8):
    for _ in range(cycles):
        app.processEvents()


def main():
    browser_calls = []
    qt_gui.webbrowser.open = lambda url: browser_calls.append(url)
    qt_gui.MainWindow.fetch_initial_async = lambda self: None
    core.InternetMonitor = QuietMonitor

    app = QApplication.instance() or QApplication(sys.argv)
    window = qt_gui.MainWindow()
    window.store.add_feed("https://news.example/rss", "News", "News")
    window.store.add_feed("https://tech.example/rss", "Tech", "Tech")
    window.store.upsert({
        "id": "news-1",
        "title": "News item",
        "link": "https://news.example/article",
        "summary": "A regression-test article.",
        "published": "2026-08-18",
        "image_url": "",
        "video_url": "",
        "video_type": "",
    }, "https://news.example/rss")
    window.show()
    window.refresh_all()
    process_events(app)

    window.fetch_feed_async = lambda _url, notify=False: None
    baseline_windows = set(app.topLevelWidgets())
    window.select_feed("https://news.example/rss")
    process_events(app)

    assert window.isVisible(), "Selecting a feed must not close the application window."
    assert window.active_feed == "https://news.example/rss", "Selected feed was not retained."
    assert not browser_calls, "Selecting a feed must never open a browser tab."
    extra_windows = [widget for widget in app.topLevelWidgets() if widget not in baseline_windows and widget.isVisible()]
    if extra_windows:
        details = [f"{type(widget).__name__}: {widget.windowTitle()!r}" for widget in extra_windows]
        raise AssertionError(f"Selecting a feed created transient top-level windows: {details}")

    video_item = {
        "title": "Direct video",
        "link": "https://news.example/video",
        "summary": "A direct-video test item.",
        "video_url": "https://media.w3.org/2010/05/sintel/trailer.mp4",
        "video_type": "direct",
    }
    detail = qt_gui.DetailDialog(video_item, window)
    play_buttons = [button for button in detail.findChildren(qt_gui.QPushButton) if button.text() == qt_gui.t("play_video")]
    assert play_buttons, "Video items must expose an in-app play control."
    play_buttons[0].click()
    process_events(app)

    assert not browser_calls, "Direct-video playback must stay in the app when internal playback is enabled."
    video_dialogs = [widget for widget in app.topLevelWidgets() if isinstance(widget, qt_gui.VideoDialog) and widget.isVisible()]
    assert len(video_dialogs) == 1, "Direct-video playback must show exactly one in-app player dialog."
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline and video_dialogs[0].player.playbackState() != qt_gui.QMediaPlayer.PlayingState:
        app.processEvents()
        time.sleep(0.1)
    assert video_dialogs[0].player.playbackState() == qt_gui.QMediaPlayer.PlayingState, "A valid direct MP4 must start in the in-app player."
    video_dialogs[0].close()
    detail.close()
    window.close()
    process_events(app)


if __name__ == "__main__":
    main()
