# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-08-18

### Added
- Keyboard shortcuts for fast reading: `Space` scrolls the current list, `B` toggles the selected article bookmark, and `O` opens its source link.
- Advanced article search with text, date-range, unread-only and bookmarked-only filters.
- Per-feed unread counters in the sidebar, a one-click **Mark all as read** action, and popularity sorting based on click count.
- Right-click card menu for bookmarking, copying a link, opening the source and launching Reader Mode.
- Feed categories with category-aware sidebar grouping and improved default Persian news sources: BBC Persian, IRNA, ISNA, Mehr and Tabnak.
- Reader Mode for extracting a clean, distraction-free article body from the original link.
- Bookmark exports in HTML and PDF formats, plus OPML import/export for transferring feed subscriptions.
- Optional desktop notifications for newly discovered articles, a font-size slider, and configurable auto-scroll.
- Automated tests for categories, unread state, advanced search, popularity sorting, OPML transfer and bookmark HTML export.

### Changed
- Expanded the local SQLite schema with a backward-compatible feed category migration.
- Extended settings persistence for notifications, auto-scroll speed and new sorting choices.
- Updated runtime dependencies for Reader Mode, notifications and PDF export.

## [1.0.0] - 2025-01-01

### Added
- **DNS-over-HTTPS**: Full DoH implementation with multiple providers
- **Video Playback**: Support for YouTube, Vimeo, Redgifs, and direct videos
- **Dual UI Styles**: Telegram-style chat and Reddit-style card views
- **Multi-language**: Complete English and Persian (Farsi) translation
- **Smart Caching**: Intelligent feed caching with expiration
- **Internet Monitor**: Real-time network status detection
- **DNS Scanner**: Test and select fastest DNS servers automatically
- **Settings Persistence**: Save user preferences between sessions
- **Comprehensive Testing**: Unit tests for core functionality

### Changed
- Improved error handling throughout the application
- Enhanced video detection algorithms
- Optimized DNS resolution performance
- Better memory management and cleanup
- Refactored code structure for maintainability

### Fixed
- DNS resolution issues in restricted networks
- Video playback reliability with VLC integration
- Image loading and display problems
- Memory leaks in long-running sessions
- UI responsiveness during feed updates

## [0.9.0] - 2024-12-15

### Added
- Basic RSS feed parsing and display
- DNS-over-HTTPS foundation
- Video detection framework
- Persian language support (initial)
- Basic caching system
- Settings management
- Logging system

### Changed
- Initial project structure
- Basic error handling
- UI layout improvements

### Fixed
- Basic bug fixes and stability improvements

## [0.8.0] - 2024-12-01

### Added
- Project initialization
- Core RSS parsing functionality
- Basic Tkinter UI framework
- DNS resolution utilities
- Video link detection

---

## Versioning Scheme

- **MAJOR** version for incompatible API changes
- **MINOR** version for functionality added in a backward compatible manner
- **PATCH** version for backward compatible bug fixes

## Release Types

- **Stable**: Production-ready releases (v1.0.0+)
- **Beta**: Feature-complete but may have minor issues (v0.9.0)
- **Alpha**: Early development releases (v0.8.0)

## Support Policy

- **Current Stable**: Full support, security patches, bug fixes
- **Previous Stable**: Security patches only
- **Beta/Alpha**: Community support, no guarantees

---

*This changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.*