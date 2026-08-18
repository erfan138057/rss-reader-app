#!/usr/bin/env python3
"""Unit tests for RSS Reader Pro core functionality."""
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import core
import config
import gui


class MockEntry:
    def __init__(self, link=None, summary=None, media_thumbnail=None):
        self.link = link
        self.summary = summary
        self.media_thumbnail = media_thumbnail


def make_item(item_id, title="Test Article", published="2026-08-18T12:00:00", clicks=0):
    return {
        "id": item_id,
        "title": title,
        "link": f"https://example.test/{item_id}",
        "summary": f"Summary for {title}",
        "published": published,
        "image_url": "",
        "video_url": "",
        "video_type": "",
        "click_count": clicks,
    }


class CoreHelpersTests(unittest.TestCase):
    def test_detect_video(self):
        url, video_type = core.detect_video(MockEntry(link="https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
        self.assertIn("youtube.com/watch?v=dQw4w9WgXcQ", url)
        self.assertEqual(video_type, "youtube")

        url, video_type = core.detect_video(MockEntry(link="https://redgifs.com/watch/coolvideo123"))
        self.assertEqual(video_type, "redgifs")
        self.assertIn("redgifs.com/watch/coolvideo123", url)

        url, video_type = core.detect_video(MockEntry(link="https://example.com/video.mp4"))
        self.assertEqual((url, video_type), ("https://example.com/video.mp4", "direct"))

    def test_image_extraction_and_cache(self):
        entry = MockEntry(media_thumbnail=[{"url": "https://example.com/image.jpg"}])
        self.assertEqual(core.extract_image_from_feed_entry(entry), "https://example.com/image.jpg")
        core.clear_cache()
        core._feed_cache["test"] = ([{"title": "Test"}], core.time.time())
        self.assertIn("test", core._feed_cache)
        core.clear_cache()
        self.assertFalse(core._feed_cache)

    def test_ip_detection(self):
        self.assertTrue(core._is_ip("192.168.1.1"))
        self.assertFalse(core._is_ip("example.com"))


class VideoPlayerRoutingTests(unittest.TestCase):
    def test_system_player_is_default(self):
        self.assertFalse(config.DEFAULTS["video_internal"])

    def test_custom_player_path_is_used_when_configured(self):
        window = gui.VideoWindow.__new__(gui.VideoWindow)
        window._external_player_path = "/opt/player/custom-player"
        window._url = "https://example.test/video.mp4"
        with mock.patch("gui.os.path.isfile", return_value=True), \
             mock.patch("subprocess.Popen") as popen:
            gui.VideoWindow._open_system(window)
        popen.assert_called_once_with(["/opt/player/custom-player", "https://example.test/video.mp4"])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "reader.db")
        self.store = core.Store(self.db_path)

    def tearDown(self):
        self.store.conn.close()
        self.temp_dir.cleanup()

    def test_categories_unread_and_mark_all_read(self):
        self.store.add_feed("https://news.example/rss", "News", "اخبار")
        self.store.add_feed("https://tech.example/rss", "Tech", "فناوری")
        feeds = self.store.get_feeds()
        self.assertEqual({feed["category"] for feed in feeds}, {"اخبار", "فناوری"})

        self.assertTrue(self.store.upsert(make_item("article-1"), "https://news.example/rss"))
        self.assertFalse(self.store.upsert(make_item("article-1", "Updated"), "https://news.example/rss"))
        self.assertEqual(self.store.get_unread_counts(), {"https://news.example/rss": 1})
        self.assertEqual(self.store.mark_all_seen("https://news.example/rss"), 1)
        self.assertEqual(self.store.get_unread_counts(), {})

    def test_feed_scoped_ids_prevent_cross_feed_collisions(self):
        news, tech = "https://news.example/rss", "https://tech.example/rss"
        self.store.add_feed(news, "News", "اخبار")
        self.store.add_feed(tech, "Tech", "فناوری")
        self.assertTrue(self.store.upsert(make_item("article-1", "News item"), news))
        self.assertTrue(self.store.upsert(make_item("article-1", "Tech item"), tech))
        news_item = self.store.get_items(news)[0]
        tech_item = self.store.get_items(tech)[0]
        self.assertEqual(news_item["title"], "News item")
        self.assertEqual(tech_item["title"], "Tech item")
        self.assertNotEqual(news_item["id"], tech_item["id"])

    def test_advanced_search_and_popularity_sort(self):
        feed = "https://news.example/rss"
        self.store.add_feed(feed, "News", "اخبار")
        self.store.upsert(make_item("article-1", "Python release", "2026-08-10T10:00:00"), feed)
        self.store.upsert(make_item("article-2", "Sports update", "2026-08-12T10:00:00"), feed)
        items = {item["title"]: item["id"] for item in self.store.get_items(feed)}
        self.store.mark_seen(items["Sports update"])
        self.store.mark_seen(items["Sports update"])
        self.store.toggle_bookmark(items["Python release"])

        results = self.store.search_items("python", feed, bookmarked_only=True,
                                          start_date="2026-08-01", end_date="2026-08-31")
        self.assertEqual([item["title"] for item in results], ["Python release"])
        self.assertEqual(self.store.get_items(feed, "popularity")[0]["title"], "Sports update")

    def test_opml_and_bookmark_html_export(self):
        self.store.add_feed("https://news.example/rss", "News", "اخبار")
        self.store.add_feed("https://tech.example/rss", "Tech", "فناوری")
        self.store.upsert(make_item("article-1", "Saved news"), "https://news.example/rss")
        self.store.toggle_bookmark(self.store.get_items("https://news.example/rss")[0]["id"])

        opml_path = os.path.join(self.temp_dir.name, "feeds.opml")
        html_path = os.path.join(self.temp_dir.name, "bookmarks.html")
        pdf_path = os.path.join(self.temp_dir.name, "bookmarks.pdf")
        self.store.export_opml(opml_path)
        self.store.export_bookmarks_html(html_path)
        self.store.export_bookmarks_pdf(pdf_path)
        self.assertTrue(Path(opml_path).exists())
        self.assertIn("https://news.example/rss", Path(opml_path).read_text(encoding="utf-8"))
        self.assertIn("Saved news", Path(html_path).read_text(encoding="utf-8"))
        self.assertTrue(Path(pdf_path).read_bytes().startswith(b"%PDF"))

        imported = core.Store(os.path.join(self.temp_dir.name, "imported.db"))
        try:
            self.assertEqual(imported.import_opml(opml_path), 2)
            self.assertEqual(len(imported.get_feeds()), 2)
        finally:
            imported.conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
