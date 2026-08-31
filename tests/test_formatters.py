import unittest

from academic_clipboard.formatters import (
    doi_markdown,
    fenced_code,
    format_bibtex,
    markdown_note,
    normalize_doi,
    url_markdown,
)


class FormatterTests(unittest.TestCase):
    def test_normalize_doi_url_and_trailing_punctuation(self) -> None:
        self.assertEqual(normalize_doi("https://doi.org/10.1000/ABC.123)."), "10.1000/abc.123")
        self.assertEqual(doi_markdown("doi: 10.1000/xyz"), "[10.1000/xyz](https://doi.org/10.1000/xyz)")

    def test_bibtex_preserves_nested_braces(self) -> None:
        raw = '@Article{Key,title={{A, Nested} Title},author="Doe, Jane",year={2025}}'
        expected = (
            '@article{Key,\n  title = {{A, Nested} Title},\n  author = "Doe, Jane",\n  year = {2025},\n}'
        )
        self.assertEqual(format_bibtex(raw), expected)

    def test_markdown_note_contains_research_sections(self) -> None:
        note = markdown_note("  A   Useful Paper  ")
        self.assertTrue(note.startswith("# A Useful Paper\n"))
        self.assertIn("## Key claims", note)

    def test_fenced_code_uses_longer_fence_when_needed(self) -> None:
        result = fenced_code("print('x')\n```", "python")
        self.assertTrue(result.startswith("````python\n"))
        self.assertTrue(result.endswith("\n````"))

    def test_github_markdown_label(self) -> None:
        self.assertEqual(
            url_markdown("https://github.com/openai/openai-python"),
            "[openai / openai-python](https://github.com/openai/openai-python)",
        )


if __name__ == "__main__":
    unittest.main()
