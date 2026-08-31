import json
import tempfile
import unittest
from pathlib import Path

from academic_clipboard.storage import ClipboardStore


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = ClipboardStore(self.root / "nested" / "clipboard.db")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_add_deduplicates_and_counts(self) -> None:
        first = self.store.add("10.1000/example")
        second = self.store.add("10.1000/example")
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.copy_count, 2)
        self.assertEqual(self.store.count(), 1)

    def test_search_kind_and_requested_order(self) -> None:
        doi = self.store.add("10.1000/example")
        title = self.store.add("A Carefully Designed Research Paper Title")
        self.assertEqual([item.id for item in self.store.list_items(kind="doi")], [doi.id])
        self.assertEqual([item.id for item in self.store.list_items(search="Carefully")], [title.id])
        self.assertEqual([item.id for item in self.store.get_many([title.id, doi.id])], [title.id, doi.id])

    def test_mark_copied_pin_and_clear_unpinned(self) -> None:
        pinned = self.store.add("10.1000/pinned")
        removed = self.store.add("A Different Research Paper Worth Reading")
        self.store.mark_copied([pinned.id])
        copied = self.store.get_many([pinned.id])[0]
        self.assertEqual(copied.copy_count, 2)
        self.assertTrue(copied.last_copied_at)
        self.store.toggle_pinned([pinned.id])
        self.assertEqual(self.store.clear_unpinned(), 1)
        self.assertEqual([item.id for item in self.store.list_items()], [pinned.id])
        self.assertNotIn(removed.id, [item.id for item in self.store.list_items()])

    def test_prune_max_items(self) -> None:
        for index in range(5):
            self.store.add(f"Plain captured paragraph number {index}.")
        removed = self.store.prune(max_items=2, retention_days=365)
        self.assertEqual(removed, 3)
        self.assertEqual(self.store.count(), 2)

    def test_exports(self) -> None:
        self.store.add("10.1000/export")
        json_path = self.root / "out" / "history.json"
        markdown_path = self.root / "out" / "history.md"
        self.store.export_json(json_path)
        self.store.export_markdown(markdown_path)
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))[0]["kind"], "doi")
        self.assertIn("https://doi.org/10.1000/export", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
