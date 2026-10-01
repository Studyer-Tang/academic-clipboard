# Changelog

## 0.5.0 preview

- Add macOS native text/image pasteboard, menu bar item, registered global hotkey, Command shortcuts, dark-mode/language preference and per-user login launch. Keep Windows tray support.
- Read clipboard payloads only after ownership changes; respect private pasteboard markers, pause before reads, keep polling after recoverable errors, remove the two-second image-copy suppression window.
- Bound history previews to 240 characters and load selected contents on demand. Add unpinned byte-budget retention, image limits, literal `%`/`_` search and safe settings defaults.
- Add opt-in PDF line cleanup, source/locator quotes, tab-separated tables for Word/Excel and lossless BibTeX export. Fix nested LaTeX delimiters and table escaping. Remove JSON export's 5000-item truncation.
- Build self-contained Windows ZIP and macOS arm64/Intel DMGs with packaged desktop smoke tests and SHA-256 checksums. These are unsigned previews.
- Document research evidence, reproducible measurements and remaining compatibility boundaries.

All notable changes will be documented here.

## 0.4.0 - 2026-09-06

- Reworked the compact window into a low-noise, single-language research drawer with three primary actions.
- Added type-specific copy transformations for DOI, BibTeX, URLs, paper titles, code, formulae, tables, and quotations.
- Added offline GB/T 7714 and APA-style reference drafts derived from captured BibTeX metadata.
- Added tab-separated and Markdown table recognition with Markdown and LaTeX table output.
- Added LaTeX formula recognition and inline/display transformations.
- Added project, source, locator, and research-note fields with automatic migration, search, and export support.
- Allowed screenshots and figures to carry the same research context without altering their image payload.
- Replaced the green prototype palette with a neutral research-tool theme and restrained indigo accent.
- Added checksums and automatic GitHub Release publishing for version tags.

## 0.3.1 - 2026-09-01

- Added an in-place screenshot thumbnail card to the compact floating window.
- Automatically selects and previews a newly captured screenshot without expanding the window.
- Added double-click copy directly from the compact thumbnail.
- Normalized opaque image color modes so copy-back and restart cannot create a duplicate screenshot.

## 0.3.0 - 2026-09-01

- Added automatic Windows screenshot and image clipboard capture.
- Added persistent, deduplicated local PNG storage and expanded-view image previews.
- Added copying saved images back to the Windows clipboard.
- Added transparent database migration and synchronized image cleanup on delete, clear, and prune.
- Added image filtering and image metadata to JSON and Markdown exports.

## 0.2.0 - 2026-08-31

- Fixed compact-window actions at high Windows display scaling with a responsive grid layout.
- Added a configurable Windows global hotkey, keyboard navigation, numbered quick copy, and copy-to-hide.
- Added snippet title/content editing, tags, tag search, context actions, and transparent v0.1 migration.
- Added system/light/dark themes and an in-app settings dialog.
- Added an in-app bilingual shortcut guide, a compact `?` help button, and `F1` access.
- Added a tag-triggered GitHub workflow for a terminal-free Windows executable.

## 0.1.0 - 2026-08-31

- Added local text clipboard monitoring and SQLite history.
- Added multi-selection and merged original/formatted copying.
- Added DOI, BibTeX, research-title, code, and URL classification.
- Added search, filters, pinning, deletion, retention, and JSON/Markdown export.
- Added default sensitive-content filtering and bilingual desktop labels.
- Added a compact, always-on-top floating window as the default reading companion, with one-click expansion.
- Added a Windows system-tray lifecycle, terminal-free launcher, per-user startup management, and single-instance protection.
- Added a CLI, automated tests, and cross-platform CI.
