"""Reproducible synthetic storage benchmark; does not access the user's data."""

import gc
import json
import tempfile
import time
import tracemalloc
from pathlib import Path

from academic_clipboard.storage import ClipboardStore


def measure(operation):
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter()
    rows = operation()
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "rows": len(rows),
        "milliseconds": round(elapsed * 1000, 2),
        "python_peak_mib": round(peak / 1024**2, 3),
    }


def main():
    with tempfile.TemporaryDirectory(prefix="academic-benchmark-") as temporary:
        store = ClipboardStore(Path(temporary) / "test.db")
        for index in range(500):
            store.add(f"Study {index}. " + "Synthetic research text. " * 4000)
        results = {
            "fixture": "500 clips, about 96,000 characters each",
            "full_history_query": measure(store.list_items),
            "preview_query": measure(lambda: store.list_items(previews=True)),
            "search_preview": measure(lambda: store.list_items("Study 42.", previews=True)),
        }
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
