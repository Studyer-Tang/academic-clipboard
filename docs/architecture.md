# Architecture

A small offline application, not a browser runtime: Python + Tk/ttk + SQLite + Pillow. On macOS, only the Cocoa PyObjC bindings are included; on Windows, pystray handles the tray. No full PyObjC framework collection, Electron, server, OCR engine or model download.

```text
UI / CLI
  ├─ clipboard state → privacy gate → classification → SQLite + PNG
  ├─ list: bounded previews → selected item: full content
  └─ explicit copy transforms → native clipboard
```

- `clipboard.py`: OS ownership counter and macOS privacy markers/text. Windows uses `GetClipboardSequenceNumber`; macOS uses `NSPasteboard.changeCount`. Unchanged data is not fetched or encoded again. Linux keeps the content-comparison fallback.
- `images.py`: bounded PNG conversion, native macOS pasteboard, Windows DIB copy. Copied file paths are not ingested as images.
- `app.py`, `ui.py`, `dialogs.py`: Tk orchestration, widget layout and dialogs. OS callbacks enqueue actions; only Tk's main thread mutates widgets. Pausing stops content reads, not just writes. Hidden startup is allowed only when a tray/menu item exists.
- `hotkeys.py`, `mac_hotkey.py`: Windows registered hotkey / Carbon registered hotkey. No keyboard hook, keystroke logger or Accessibility grant. macOS key names use ANSI physical positions; modifier names include Cmd and Option.
- `tray.py`, `mac_tray.py`: platform tray adapters. Cocoa menu creation/removal stays on the main thread; Tk owns its event loop. No competing Cocoa `run()`/`stop()` loop.
- `storage.py`: schema migration, deduplication, literal search, full-content reads on demand, streaming JSON/BibTeX export, retention by age/count/payload bytes. Pinned items are exempt. SQLite pages are reused after deletion; the payload budget is not a hard bound on the database file or pinned data.
- `transforms.py`: pure, deterministic copy transforms. PDF cleanup is opt-in, saved originals stay intact, sources are user-provided, reference drafts require verification.
- `settings.py`, `single_instance.py`, `startup.py`: typed/clamped settings, atomic saves, per-user mutex/POSIX file lock, optional Windows Run key/macOS LaunchAgent. No privileged service.

The GUI shows up to 500 matching previews; search still covers the complete database. JSON/BibTeX exports stream all matching stored items without the GUI result cap. JSON/Markdown contain image paths, not bundled image binaries: back up the data directory for a complete image backup.

Builds use PyInstaller **onedir**, so startup does not unpack Python into a temporary folder on every run. Each OS/CPU architecture is built natively, with packaged-binary smoke tests before publication. See [research and validation](research-and-validation.md) for measurements and limitations.
