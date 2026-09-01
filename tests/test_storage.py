import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from io import BytesIO
from pathlib import Path

from PIL import Image

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

    def test_edit_tags_search_and_custom_title_survive_recapture(self) -> None:
        item = self.store.add("A Useful Research Paper for Editing")
        updated = self.store.update(
            item.id,
            "A Useful Research Paper for Editing",
            "My reading note",
            "causal, methods, causal",
        )
        self.assertEqual(updated.title, "My reading note")
        self.assertEqual(updated.tags, "causal, methods")
        self.assertEqual(self.store.list_items(search="methods")[0].id, item.id)
        recaptured = self.store.add("A Useful Research Paper for Editing")
        self.assertEqual(recaptured.title, "My reading note")

    def test_edit_rejects_duplicate_content(self) -> None:
        first = self.store.add("10.1000/first")
        second = self.store.add("10.1000/second")
        with self.assertRaisesRegex(ValueError, "same text"):
            self.store.update(second.id, first.content, second.title)

    def test_existing_v01_database_is_migrated(self) -> None:
        legacy_path = self.root / "legacy.db"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.execute(
                """
                CREATE TABLE clipboard_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    normalized_content TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    subtype TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_copied_at TEXT NOT NULL DEFAULT '',
                    copy_count INTEGER NOT NULL DEFAULT 1,
                    pinned INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.commit()
        migrated = ClipboardStore(legacy_path)
        item = migrated.add("10.1000/migrated")
        self.assertEqual(item.tags, "")
        self.assertEqual(item.media_path, "")
        self.assertEqual(item.width, 0)
        self.assertEqual(item.height, 0)
        self.assertEqual(migrated.update(item.id, item.content, item.title, "legacy").tags, "legacy")

    def image_bytes(self, color: str = "navy") -> bytes:
        output = BytesIO()
        Image.new("RGB", (32, 18), color).save(output, format="PNG")
        return output.getvalue()

    def test_add_image_persists_and_deduplicates(self) -> None:
        first = self.store.add_image(self.image_bytes(), 32, 18)
        second = self.store.add_image(self.image_bytes(), 32, 18)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.kind, "image")
        self.assertEqual(second.subtype, "screenshot")
        self.assertEqual((second.width, second.height), (32, 18))
        self.assertEqual(second.copy_count, 2)
        media_file = self.store.media_file(second)
        self.assertIsNotNone(media_file)
        assert media_file is not None
        self.assertTrue(media_file.exists())

    def test_deleting_and_clearing_images_removes_local_files(self) -> None:
        deleted = self.store.add_image(self.image_bytes("red"), 32, 18)
        deleted_file = self.store.media_file(deleted)
        self.store.delete([deleted.id])
        assert deleted_file is not None
        self.assertFalse(deleted_file.exists())

        cleared = self.store.add_image(self.image_bytes("green"), 32, 18)
        cleared_file = self.store.media_file(cleared)
        self.store.clear_all()
        assert cleared_file is not None
        self.assertFalse(cleared_file.exists())

    def test_pruning_images_removes_only_discarded_files(self) -> None:
        first = self.store.add_image(self.image_bytes("purple"), 32, 18)
        second = self.store.add_image(self.image_bytes("orange"), 32, 18)
        files = {self.store.media_file(first), self.store.media_file(second)}
        self.assertEqual(self.store.prune(max_items=1, retention_days=365), 1)
        self.assertEqual(sum(bool(path and path.exists()) for path in files), 1)
        remaining = self.store.list_items(kind="image")
        self.assertEqual(len(remaining), 1)
        self.assertTrue(self.store.media_file(remaining[0]).exists())

    def test_image_export_contains_local_metadata(self) -> None:
        item = self.store.add_image(self.image_bytes(), 32, 18)
        json_path = self.root / "images.json"
        markdown_path = self.root / "images.md"
        self.store.export_json(json_path)
        self.store.export_markdown(markdown_path)
        payload = json.loads(json_path.read_text(encoding="utf-8"))[0]
        self.assertEqual(payload["media_path"], item.media_path)
        self.assertEqual(payload["width"], 32)
        markdown = markdown_path.read_text(encoding="utf-8")
        self.assertIn("Dimensions: 32×18", markdown)
        self.assertIn(item.media_path, markdown)


if __name__ == "__main__":
    unittest.main()
