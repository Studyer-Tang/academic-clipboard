import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from academic_clipboard.cli import main
from academic_clipboard.storage import ClipboardStore


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "clipboard.db"
        store = ClipboardStore(self.database)
        store.add("10.1000/cli")
        store.add("A Useful Research Paper for Testing")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["--database", str(self.database), *arguments])
        return code, output.getvalue()

    def test_list_json_and_search(self) -> None:
        code, output = self.run_cli("list", "--kind", "doi", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)[0]["kind"], "doi")
        _, search = self.run_cli("search", "Useful")
        self.assertIn("Useful Research Paper", search)

    def test_stats_export_and_clear(self) -> None:
        _, stats = self.run_cli("stats")
        self.assertIn("items=2", stats)
        destination = self.root / "export.md"
        self.run_cli("export", str(destination))
        self.assertTrue(destination.exists())
        _, cleared = self.run_cli("clear", "--all", "--yes")
        self.assertIn("deleted=2", cleared)


if __name__ == "__main__":
    unittest.main()
