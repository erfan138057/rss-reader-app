# Version Information

__version__ = "1.0.0"
__release_date__ = "2025-01-01"
__status__ = "Stable"
__build__ = "20250101"

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