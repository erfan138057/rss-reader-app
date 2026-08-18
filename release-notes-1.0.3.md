# RSS Reader Pro v1.0.3

**Release date:** 2026-08-18  
**Status:** Stable

RSS Reader Pro v1.0.3 focuses on a smoother, faster reading workflow. This release introduces richer discovery and organization tools while keeping the application local-first and compatible with existing SQLite databases.

## Highlights

| Area | What is new |
|---|---|
| Fast navigation | Press `Space` to scroll the current feed, `B` to toggle the bookmark for the active article, and `O` to open its source link. |
| Search and sorting | Use free-text search together with date-range, unread-only and bookmarked-only filters. Sort articles by newest, oldest or popularity based on click count. |
| Feed organization | Group feeds into categories such as News, Tech and Sports. The sidebar now shows unread counts beside each feed. |
| Card actions | Right-click a card to bookmark it, copy its link, open it in the browser or start Reader Mode. |
| Reader Mode | Open a simplified, distraction-free article body extracted from the original page. |
| Portability | Transfer subscriptions with OPML import/export, and save bookmarks as HTML or PDF. |
| Reading comfort | Enable desktop notifications for newly discovered items, adjust font size with a slider and turn on auto-scroll. |

## Persian sources by default

New installations include improved Persian defaults from **BBC Persian**, **IRNA**, **ISNA**, **Mehr**, and **Tabnak**, alongside BBC News and The Guardian for broader coverage. Existing user-added and user-deleted feeds remain respected.

## Compatibility and dependencies

The feed database migration adds a category column automatically and preserves prior feeds, bookmarks and reading state. Reader Mode, desktop notifications and PDF export add `beautifulsoup4`, `plyer` and `reportlab` to the runtime dependencies.

## Packaging and platform support

The packaged Qt application now uses the official Signal Midnight icon on its application window, taskbar and Windows executable. The release includes a portable `x86_64` Linux archive in addition to the Windows EXE. Linux users extract the archive and run `RSS-Reader-Pro` directly; no VLC installation is required.

The Windows workflow is prepared for Microsoft Artifact Signing with SHA-256 and RFC 3161 timestamping. The protected signing step activates after the owner configures the required Azure identity, account and certificate-profile settings. See `docs/SMARTSCREEN.md` for the configuration and the reputation-based behavior of SmartScreen.

## Regression fixes

Selecting a feed no longer detaches cards into temporary top-level widgets during the visual refresh, eliminating the short-lived flashing surface reported by users. The selected-feed refresh is now quiet and does not issue a new-item notification solely because the user chose a feed.

Direct MP4 and other compatible direct media now open in the native Qt player inside the application. The player includes play/pause, native audio/video output, an explanatory in-app error state and a deliberate fallback button for the user’s system player. Provider pages such as YouTube, Vimeo and Redgifs remain delegated to the system handler because they are not direct media streams.

## Quality checks

The release passed Python compilation checks, nine core automated tests and two Qt regression tests covering feed selection, browser/tab suppression and in-app video player routing. A separate headless behavioral check starts playback of a real public direct MP4 in the native Qt player. The portable Linux archive was built with PyInstaller, checked for the required bundled XCB dependencies, smoke-tested with Qt's offscreen platform and inspected after packaging.

## Upgrade

```bash
git pull
pip install -r requirements.txt
python gui.py
```

Windows executable users can download the EXE from the release. Linux users can download `RSS-Reader-Pro-v1.0.3-linux-x86_64.tar.gz`, extract it and execute `RSS-Reader-Pro`.
