# Architecture

Academic Clipboard deliberately uses a small layered design:

```text
Tkinter UI / CLI
       |
ClipboardStore (SQLite)
       |
classifier -> formatters
       |
privacy filter (before storage)
```

- `app.py` owns clipboard polling and desktop interactions. It never writes SQL directly.
- `cli.py` exposes read, search, export, statistics, and clearing operations.
- `storage.py` owns schema creation, deduplication, retention, ordering, and exports.
- `classifier.py` performs deterministic, offline classification.
- `formatters.py` produces reusable Markdown and BibTeX representations.
- `privacy.py` rejects common secret patterns before the GUI calls storage.
- `settings.py` resolves per-platform data directories and persists non-secret preferences.
- `tray.py` owns the generated tray icon and menu; callbacks are queued back onto Tk's UI thread.
- `startup.py` provides detached `pythonw` launch and per-user Windows startup registration.
- `single_instance.py` prevents duplicate Windows clipboard listeners with a named mutex.

There is no network layer. This keeps v0.1 auditable and makes offline use the default. Future integrations should be opt-in and must not upload clipboard history silently.
