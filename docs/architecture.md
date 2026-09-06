# Architecture

Academic Clipboard deliberately uses a small layered design:

```text
Tkinter UI / CLI
       |
ClipboardStore (SQLite)
       |-- images/ (local PNG files)
       |
classifier -> formatters / academic transforms
       |
privacy filter (before storage)
```

- `app.py` owns clipboard polling and desktop interactions. It never writes SQL directly.
- `cli.py` exposes read, search, export, statistics, and clearing operations.
- `storage.py` owns schema creation, deduplication, retention, ordering, and exports.
- `images.py` converts clipboard bitmaps to PNG and restores saved images to the Windows clipboard.
- `classifier.py` performs deterministic, offline classification.
- `formatters.py` produces reusable Markdown and BibTeX representations.
- `transforms.py` exposes content-aware copy actions for citations, DOI links, formulae, tables,
  code, and research notes. Citation drafts only use fields already present in captured BibTeX.
- Research context (project, source, locator, and note) is stored beside each clip, included in
  local search, and exported without requiring a separate cloud account.
- `privacy.py` rejects common secret patterns before the GUI calls storage.
- `settings.py` resolves per-platform data directories and persists non-secret preferences.
- `tray.py` owns the generated tray icon and menu; callbacks are queued back onto Tk's UI thread.
- `hotkeys.py` owns Windows `RegisterHotKey` parsing and the background message loop.
- `dialogs.py` owns snippet editing and application settings dialogs.
- `theme.py` defines light/dark palettes and applies the ttk design system.
- `startup.py` provides detached `pythonw` launch and per-user Windows startup registration.
- `single_instance.py` prevents duplicate Windows clipboard listeners with a named mutex.

There is no network layer. Text metadata stays in SQLite and screenshots stay in the adjacent `images/` directory. This keeps the application auditable and offline by default. Future integrations should be opt-in and must not upload clipboard history silently.
