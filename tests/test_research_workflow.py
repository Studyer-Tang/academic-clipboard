import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from academic_clipboard.storage import ClipboardStore
from academic_clipboard.transforms import (
    available_transforms,
    bibtex_reference,
    clean_pdf_text,
    latex_table,
    table_rows,
)


class ResearchWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = ClipboardStore(Path(self.temporary.name) / "history.db")

    def test_pdf_cleanup_preserves_paragraphs_and_requires_opt_in_for_hyphens(self):
        text = "An inter-\nnational ﬁnding.\nMore evidence.\n\n中文\n研究。"
        self.assertEqual(clean_pdf_text(text), "An inter- national finding. More evidence.\n\n中文研究。")
        self.assertIn("international", clean_pdf_text(text, dehyphenate=True))
        self.assertIn("well-known", clean_pdf_text("well-known fact", dehyphenate=True))

    def test_source_copy_keeps_original_and_locator(self):
        item = self.store.add("First line.\nSecond line.")
        item = self.store.update_context(item.id, "Test", source="Paper A", locator="p. 7")
        transforms = {item.key: item.value for item in available_transforms(item)}
        self.assertEqual(transforms["source-quote"], "> First line.\n> Second line.\n\n— Paper A · p. 7")
        self.assertEqual(self.store.get_many([item.id])[0].content, "First line.\nSecond line.")

    def test_formula_delimiters_are_not_nested(self):
        for formula in (r"\[x+y\]", r"\(x+y\)", "$$x+y$$", "$x+y$"):
            item = self.store.add(formula)
            transforms = {item.key: item.value for item in available_transforms(item)}
            self.assertEqual(transforms["inline-latex"], r"\(x+y\)")

    def test_table_copy_and_latex_escaping(self):
        item = self.store.add("Name\tValue\nCost\t$5_{x}")
        transforms = {item.key: item.value for item in available_transforms(item)}
        self.assertEqual(transforms["tsv-table"], item.content)
        self.assertIn(r"\$5\_\{x\}", latex_table(item.content))

    def test_empty_table_cells_and_literal_pipes_survive_conversion(self):
        self.assertEqual(table_rows("\tvalue\t\n1\t2\t3"), [["", "value", ""], ["1", "2", "3"]])
        self.assertEqual(table_rows(r"| a\|b | c |"), [["a|b", "c"]])
        item = self.store.add("\tvalue\t\n1\t2\t3")
        self.assertTrue(item.normalized_content.startswith("|  | value |  |"))

    def test_edit_preserves_code_indentation_and_outer_newlines(self):
        source = "    result = 1\n    return result\n"
        item = self.store.add(source)
        self.assertEqual(self.store.update(item.id, source, "Code").content, source)

    def test_books_are_not_labelled_as_journal_articles(self):
        self.assertIn("Book[M]", bibtex_reference("@book{demo, title={Book}}", "gbt"))

    def test_list_previews_are_bounded_but_selected_text_is_complete(self):
        text = "Research finding. " * 5000
        item = self.store.add(text)
        preview = self.store.list_items(previews=True)[0]
        self.assertLessEqual(len(preview.content), 240)
        self.assertEqual(preview.normalized_content, "")
        self.assertEqual(self.store.get_many([item.id])[0].content, text)

    def test_search_treats_percent_and_underscore_as_literal(self):
        self.store.add("95% confidence x_y")
        self.store.add("Other text xyz")
        self.assertEqual(len(self.store.list_items("%")), 1)
        self.assertEqual(len(self.store.list_items("_")), 1)

    def test_size_budget_prunes_old_unpinned_payloads_but_preserves_pins(self):
        pinned = self.store.add("p" * 300000)
        self.store.toggle_pinned([pinned.id])
        old = self.store.add("a" * 300000)
        newest = self.store.add("b" * 300000)
        self.assertEqual(self.store.prune(2000, 90, max_storage_mb=1), 1)
        self.assertEqual({item.id for item in self.store.list_items()}, {pinned.id, newest.id})
        self.assertEqual(self.store.get_many([old.id]), [])

    def test_old_database_gets_payload_size_without_losing_data(self):
        item = self.store.add("A legacy note")
        with closing(sqlite3.connect(self.store.path)) as connection, connection:
            connection.execute("ALTER TABLE clipboard_items DROP COLUMN payload_bytes")
        migrated = ClipboardStore(self.store.path)
        self.assertEqual(migrated.get_many([item.id])[0].content, "A legacy note")
        with closing(sqlite3.connect(self.store.path)) as connection, connection:
            self.assertGreater(
                connection.execute("SELECT payload_bytes FROM clipboard_items").fetchone()[0], 0
            )

    def test_bibtex_export_preserves_fields_and_ignores_nonreferences(self):
        bib = "@article{demo, title={Synthetic study}, year={2026}, custom={Keep this field}}"
        self.store.add(bib)
        self.store.add("An unrelated note")
        path = Path(self.temporary.name) / "references.bib"
        self.store.export_bibtex(path)
        self.assertEqual(path.read_text().strip(), bib)

    def test_bibtex_copy_and_export_keep_the_original_multi_record_snippet(self):
        bib = (
            "@article{one,title={{First, Nested} title},year={2024}}\n"
            '@book(two,title="Second title",year=2025)'
        )
        item = self.store.add(bib)
        actions = {action.key: action.value for action in available_transforms(item)}
        self.assertEqual(actions["original"], bib)
        self.assertEqual(self.store.get_many([item.id])[0].content, bib)
        self.assertIn("@article{one,", actions["bibtex"])
        self.assertIn("@book{two,", actions["bibtex"])
        self.assertNotIn("@book", actions["apa"])
        path = Path(self.temporary.name) / "references.bib"
        self.store.export_bibtex(path)
        self.assertEqual(path.read_text().strip(), bib)

    def test_export_is_not_truncated_by_the_ui_limit(self):
        with closing(sqlite3.connect(self.store.path)) as connection, connection:
            connection.executemany(
                "INSERT INTO clipboard_items(content,content_hash,normalized_content,kind,subtype,title,created_at) "
                "VALUES (?,?,?,'text','plain','test','2026-10-01')",
                ((f"note {i}", f"hash {i}", f"note {i}") for i in range(5010)),
            )
        path = Path(self.temporary.name) / "export.json"
        self.store.export_json(path)
        self.assertEqual(len(json.loads(path.read_text())), 5010)
