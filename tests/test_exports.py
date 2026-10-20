import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from academic_clipboard.cli import main
from academic_clipboard.storage import ClipboardStore

EXPORTERS = ("export_json", "export_markdown", "export_bibtex")


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = ClipboardStore(self.root / "data" / "clipboard.db")
        self.reference = self.store.add("@article{study, title={Original evidence}, year={2026}}")
        self.store.update_context(
            self.reference.id, "Reading note", source="Paper A", locator="p. 12", note="Check the design."
        )

    def test_failed_snapshot_keeps_previous_export_and_leaves_no_partial_new_file(self):
        def interrupted_snapshot():
            yield self.reference
            raise sqlite3.OperationalError("simulated database read failure")

        destination_dir = self.root / "exports"
        destination_dir.mkdir()
        for method in EXPORTERS:
            for exists in (False, True):
                with self.subTest(format=method, exists=exists):
                    destination = destination_dir / f"{method}-{exists}"
                    if exists:
                        destination.write_bytes(b"previous complete backup")
                    before = {path.name: path.read_bytes() for path in destination_dir.iterdir()}
                    with (
                        patch.object(self.store, "iter_items", interrupted_snapshot),
                        self.assertRaisesRegex(sqlite3.OperationalError, "simulated"),
                    ):
                        getattr(self.store, method)(destination)
                    after = {path.name: path.read_bytes() for path in destination_dir.iterdir()}
                    self.assertEqual(after, before)

    def test_successful_exports_replace_old_backups_and_keep_research_fields(self):
        json_path = self.root / "exports" / "history.json"
        markdown_path = json_path.with_suffix(".md")
        bib_path = json_path.with_suffix(".bib")
        json_path.parent.mkdir()
        for path in (json_path, markdown_path, bib_path):
            path.write_text("obsolete export", encoding="utf-8")
        self.store.export_json(json_path)
        self.store.export_markdown(markdown_path)
        self.store.export_bibtex(bib_path)
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload[0]["source"], "Paper A")
        self.assertEqual(payload[0]["locator"], "p. 12")
        self.assertIn("Check the design.", markdown_path.read_text(encoding="utf-8"))
        self.assertEqual(bib_path.read_text(encoding="utf-8").strip(), self.reference.content)
        self.assertEqual(
            {path.name for path in json_path.parent.iterdir()}, {"history.json", "history.md", "history.bib"}
        )

    def test_disk_sync_and_replacement_failures_keep_previous_backup(self):
        destination = self.root / "history.export"
        for method in EXPORTERS:
            for operation in ("academic_clipboard.storage.os.fsync", "pathlib.Path.replace"):
                with self.subTest(format=method, operation=operation):
                    destination.write_bytes(b"previous complete backup")
                    before = {path.name for path in self.root.iterdir()}
                    with (
                        patch(operation, side_effect=OSError("simulated write failure")),
                        self.assertRaisesRegex(OSError, "simulated"),
                    ):
                        getattr(self.store, method)(destination)
                    self.assertEqual(destination.read_bytes(), b"previous complete backup")
                    self.assertEqual({path.name for path in self.root.iterdir()}, before)

    def test_database_and_sqlite_sidecars_cannot_be_used_as_export_destinations(self):
        before = self.store.path.read_bytes()
        for method in EXPORTERS:
            for suffix in ("", "-wal", "-shm", "-journal"):
                with self.subTest(format=method, suffix=suffix):
                    with self.assertRaisesRegex(ValueError, "must not overwrite"):
                        getattr(self.store, method)(Path(f"{self.store.path}{suffix}"))
                    self.assertEqual(self.store.path.read_bytes(), before)
                    self.assertEqual(
                        self.store.get_many([self.reference.id])[0].content, self.reference.content
                    )

    def test_database_aliases_cannot_bypass_destination_protection(self):
        for link_type in ("symlink", "hardlink"):
            alias = self.root / f"{link_type}.json"
            try:
                if link_type == "symlink":
                    alias.symlink_to(self.store.path)
                else:
                    alias.hardlink_to(self.store.path)
            except OSError as error:
                self.skipTest(f"file links unavailable: {error}")
            for method in EXPORTERS:
                with self.subTest(format=method, link=link_type):
                    with self.assertRaisesRegex(ValueError, "must not overwrite"):
                        getattr(self.store, method)(alias)
                    self.assertEqual(self.store.count(), 1)

    def test_stored_screenshots_are_not_replaced_by_exports(self):
        stream = BytesIO()
        Image.new("RGB", (2, 2), "navy").save(stream, format="PNG")
        png = stream.getvalue()
        item = self.store.add_image(png, 2, 2)
        image_path = self.store.media_file(item)
        for method in EXPORTERS:
            with self.subTest(format=method):
                with self.assertRaisesRegex(ValueError, "stored images"):
                    getattr(self.store, method)(image_path)
                self.assertEqual(image_path.read_bytes(), png)

    def test_case_variant_sqlite_sidecars_follow_the_actual_filesystem(self):
        database_alias = self.store.path.with_name(self.store.path.name.swapcase())
        case_insensitive = database_alias.exists() and database_alias.samefile(self.store.path)
        for method in EXPORTERS:
            for suffix in ("-WAL", "-SHM", "-JOURNAL"):
                for parent_alias in (False, True):
                    parent = self.store.path.parent
                    if parent_alias:
                        parent = parent.with_name(parent.name.swapcase())
                    destination = parent / (self.store.path.name.upper() + suffix)
                    with self.subTest(format=method, suffix=suffix, parent_alias=parent_alias):
                        self.assertFalse(destination.exists())
                        if case_insensitive:
                            with self.assertRaisesRegex(ValueError, "must not overwrite"):
                                getattr(self.store, method)(destination)
                            self.assertFalse(destination.exists())
                        else:
                            getattr(self.store, method)(destination)
                        self.assertEqual(self.store.count(), 1)
                        if not case_insensitive:
                            self.assertTrue(destination.exists())
                            destination.unlink()

    def test_case_variant_image_paths_do_not_overwrite_the_same_screenshot(self):
        stream = BytesIO()
        Image.new("RGB", (2, 2), "navy").save(stream, format="PNG")
        png = stream.getvalue()
        item = self.store.add_image(png, 2, 2)
        image_path = self.store.media_file(item)
        destination = (
            image_path.parent.with_name(image_path.parent.name.swapcase()) / image_path.name.swapcase()
        )
        same_image = destination.exists() and destination.samefile(image_path)
        for method in EXPORTERS:
            with self.subTest(format=method, same_image=same_image):
                if same_image:
                    with self.assertRaisesRegex(ValueError, "stored images"):
                        getattr(self.store, method)(destination)
                else:
                    getattr(self.store, method)(destination)
                    self.assertTrue(destination.exists())
                self.assertEqual(image_path.read_bytes(), png)

    def test_gui_reports_failed_export_without_showing_success(self):
        from academic_clipboard.app import AcademicClipboardApp

        app = AcademicClipboardApp.__new__(AcademicClipboardApp)
        app.root = Mock()
        app.store = self.store
        app.status_var = Mock()
        with (
            patch("academic_clipboard.app.filedialog.asksaveasfilename", return_value=str(self.store.path)),
            patch("academic_clipboard.app.messagebox.showerror") as show_error,
        ):
            app.export()
        self.assertIn("must not overwrite", show_error.call_args.args[1])
        self.assertIs(show_error.call_args.kwargs["parent"], app.root)
        self.assertEqual(app.status_var.set.call_count, 1)
        self.assertNotIn("已导出", app.status_var.set.call_args.args[0])

    def test_cli_reports_failure_without_claiming_export_success(self):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
            main(["--database", str(self.store.path), "export", str(self.store.path)])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("must not overwrite", stderr.getvalue())
        self.assertNotIn("exported=", stdout.getvalue())
        self.assertEqual(self.store.count(), 1)


if __name__ == "__main__":
    unittest.main()
