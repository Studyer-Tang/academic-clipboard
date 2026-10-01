"""Bounded desktop smoke test with synthetic history and capture disabled."""

import argparse
import json
import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path

from academic_clipboard.app import AcademicClipboardApp
from academic_clipboard.settings import Settings
from academic_clipboard.storage import ClipboardStore


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="academic-qa-") as temporary:
        home = Path(temporary)
        store = ClipboardStore(home / "clipboard.db")
        store.add("10.1038/s41586-020-2649-2")
        item = store.add("Research evidence copied\nfrom a PDF.\n\n保留原始内容以供核对。")
        store.update_context(
            item.id, "Reading excerpt / 阅读摘录", source="Synthetic test paper", locator="p. 12"
        )
        store.add("Method\tScore\nBaseline\t0.81\nProposed\t0.93")
        started = time.perf_counter()
        root = tk.Tk()
        app = AcademicClipboardApp(root, store, Settings(), home / "settings.json")
        app.toggle_capture()
        root.update()
        assert len(app.items) == 3
        assert app.tray is not None, app.status_var.get()
        assert app.hotkey and app.hotkey.registered, app.hotkey.error if app.hotkey else "no hotkey"
        app.toggle_window_mode()
        root.update()
        app.toggle_window_mode()
        app.search_var.set("Synthetic")
        app.refresh()
        assert len(app.items) == 1
        app.search_var.set("")
        app.refresh()
        elapsed = time.perf_counter() - started
        if sys.stdout is not None:
            print(f"desktop ready in {elapsed:.3f}s", flush=True)
        if not args.interactive:
            root.after(1500, app.quit)
        root.mainloop()
        if args.report:
            args.report.write_text(
                json.dumps({"ok": True, "startup_seconds": round(elapsed, 3)}), encoding="utf-8"
            )
    return 0


if __name__ == "__main__":
    main()
