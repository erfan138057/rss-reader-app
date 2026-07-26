#!/usr/bin/env python3
"""
Simple tests for core functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import *

def test_detect_video():
    """Test video detection functions."""
    print("Testing video detection...")
    
    # Test YouTube
    class MockEntry:
        def __init__(self, link=None, summary=None):
            self.link = link
            self.summary = summary
    
    # Test YouTube detection
    entry = MockEntry(link="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    url, vtype = detect_video(entry)
    assert "youtube.com/watch?v=dQw4w9WgXcQ" in url
    assert vtype == "youtube"
    print("✓ YouTube detection works")
    
    # Test Redgifs
    entry = MockEntry(link="https://redgifs.com/watch/coolvideo123")
    url, vtype = detect_video(entry)
    assert "redgifs.com/watch/coolvideo123" in url
    assert vtype == "redgifs"
    print("✓ Redgifs detection works")
    
    # Test direct video
    entry = MockEntry(link="https://example.com/video.mp4")
    url, vtype = detect_video(entry)
    assert url == "https://example.com/video.mp4"
    assert vtype == "direct"
    print("✓ Direct video detection works")

def test_doh_resolve():
    """Test DoH resolution (mock test)."""
    print("Testing DoH resolution...")
    
    # Test IP detection
    assert _is_ip("192.168.1.1") == True
    assert _is_ip("google.com") == False
    print("✓ IP detection works")

def test_image_extraction():
    """Test image extraction."""
    print("Testing image extraction...")
    
    class MockEntry:
        def __init__(self, media_thumbnail=None):
            self.media_thumbnail = media_thumbnail
    
    # Test media thumbnail
    entry = MockEntry(media_thumbnail=[{"url": "https://example.com/image.jpg"}])
    image_url = extract_image_from_feed_entry(entry)
    assert image_url == "https://example.com/image.jpg"
    print("✓ Image extraction works")

def test_cache():
    """Test caching functionality."""
    print("Testing cache...")
    
    # Clear cache first
    clear_cache()
    
    # Mock feed data
    test_data = [{"title": "Test Article"}]
    cache_key = "test_url_20"
    
    # Add to cache
    _feed_cache[cache_key] = (test_data, time.time())
    
    # Check cache
    assert cache_key in _feed_cache
    print("✓ Cache functionality works")
    
    # Clear cache
    clear_cache()
    assert len(_feed_cache) == 0
    print("✓ Cache clearing works")

if __name__ == "__main__":
    print("Running core module tests...\n")
    
    try:
        test_detect_video()
        test_doh_resolve()
        test_image_extraction()
        test_cache()
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)