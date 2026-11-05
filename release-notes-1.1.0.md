# RSS Reader Pro v1.1.0 — User Experience Update

RSS Reader Pro v1.1.0 focuses on a calmer, clearer and more dependable daily reading experience. It introduces practical improvements without changing the local-first identity of the application.

## What is new

- **Feed health at a glance:** the sidebar now shows whether a feed was loaded successfully or needs attention.
- **Retry failed feeds:** retry a feed directly from its context menu instead of deleting and adding it again.
- **Diagnostics:** inspect the application version, platform, database path, image cache and feed status from the Tools menu.
- **Safer storage:** automatic rolling database backups are created before opening and migrating an existing profile.
- **Faster images:** downloaded images use a bounded local cache with automatic cleanup.
- **More reliable refresh:** overlapping initial, manual and automatic refresh operations are blocked safely.
- **Better feed validation:** malformed or unsupported feed addresses are rejected with a clear message.
- **Improved accessibility:** stronger keyboard focus behavior and clearer controls in the Qt interface.
- **Official Windows and Linux support:** the Windows build is tested on Python 3.12 and the portable Linux build remains available.

## Privacy

This release remains local-first. There is no mandatory account, cloud synchronization, advertising or telemetry. Feed data, reading state, bookmarks and backups stay on the user’s device.

## Compatibility

Existing RSS Reader Pro profiles and SQLite databases are migrated automatically. A rolling backup is created before the application applies schema changes.

## Downloads

- Windows: `RSS-Reader-Pro-v1.1.0-windows-x64.exe`
- Linux: `RSS-Reader-Pro-v1.1.0-linux-x86_64.tar.gz`

See the GitHub release assets for the latest portable builds.
