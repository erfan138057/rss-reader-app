# Version Information

__version__ = "1.0.3"
__release_date__ = "2026-08-18"
__status__ = "Stable"
__build__ = "20260818"

# Supported Platforms
SUPPORTED_PLATFORMS = ["Windows"]

# Minimum Requirements
MINIMUM_PYTHON = "3.8"
MINIMUM_RAM = "2GB"
RECOMMENDED_RAM = "4GB"

# Feature Flags
FEATURES = {
    "doh": True,
    "video_playback": True,
    "multi_language": True,
    "caching": True,
    "dns_scanner": True,
    "internet_monitor": True,
    "persistent_settings": True,
    "feed_categories": True,
    "advanced_search": True,
    "reader_mode": True,
    "bookmark_export": True,
    "opml_transfer": True,
    "desktop_notifications": True,
    "auto_scroll": True,
}

# Video Platforms Supported
VIDEO_PLATFORMS = ["youtube", "vimeo", "redgifs", "direct"]

# DNS Providers
DNS_PROVIDERS = [
    "cloudflare", "google", "quad9", "adguard",
    "nextdns", "opendns"
]

# Languages
LANGUAGES = ["en", "fa"]

# UI Styles
UI_STYLES = ["telegram", "reddit"]