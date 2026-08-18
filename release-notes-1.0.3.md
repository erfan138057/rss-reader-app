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

## Quality checks

The release passed Python compilation checks and six automated tests covering video detection, image/cache helpers, feed categories, unread state, advanced filters, popularity sorting, OPML transfer and bookmark HTML export.

## Upgrade

```bash
git pull
pip install -r requirements.txt
python gui.py
```

Windows executable users can download a packaged build when it is attached to the release.
