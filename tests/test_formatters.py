import unittest

from academic_clipboard.formatters import (
    doi_latex,
    doi_markdown,
    doi_url,
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

    def test_bibtex_formats_each_record_separately(self) -> None:
        raw = (
            '@Article{one,title={{First, Nested} title},author="A and B",year=2024}\n'
            '@Book(two,title="Second {title}",author={C and D},year={2025})'
        )
        expected = (
            '@article{one,\n  title = {{First, Nested} title},\n  author = "A and B",\n'
            '  year = 2024,\n}\n\n@book{two,\n  title = "Second {title}",\n'
            "  author = {C and D},\n  year = {2025},\n}"
        )
        self.assertEqual(format_bibtex(raw), expected)
        self.assertEqual(format_bibtex(expected), expected)

    def test_bibtex_preserves_escaped_quotes_and_braces(self) -> None:
        raw = r'@article{key,title="A {nested, title} with \"quotes\"",note={A \{literal\} brace}}'
        formatted = format_bibtex(raw)
        self.assertIn(r'title = "A {nested, title} with \"quotes\"",', formatted)
        self.assertIn(r"note = {A \{literal\} brace},", formatted)
        self.assertEqual(format_bibtex(formatted), formatted)

    def test_bibtex_preserves_macros_and_concatenation_as_expressions(self) -> None:
        raw = '@article{key,title={Part One} # " Part Two",month=jan,year=2025}'
        formatted = format_bibtex(raw)
        self.assertIn('title = {Part One} # " Part Two",', formatted)
        self.assertIn("month = jan,", formatted)
        self.assertEqual(format_bibtex(formatted), formatted)

    def test_bibtex_rejects_partial_and_unsupported_documents(self) -> None:
        valid = "@article{first,title={Keep me},year=2024}"
        cases = (
            valid + "\n@article{second,title={Missing brace}",
            valid + '\n@article{second,title="Missing quote}',
            valid + " extra text",
            valid + "\n% preserve this comment",
            "@string{journal={Synthetic Journal}}\n" + valid,
            "@comment{Keep this}\n" + valid,
            '@preamble{"Keep this"}\n' + valid,
            "@article{key,title={Title} year=2025}",
            "@article{key,title=,year=2025}",
            "@article{key,title={Title} #}",
            "@article{key,title={Title},,year=2025}",
            '@article{key,title="A } malformed quote"}',
        )
        for raw in cases:
            with self.subTest(raw=raw):
                self.assertEqual(format_bibtex(raw), raw)

    def test_doi_preserves_balanced_delimiters_and_removes_only_extra_closers(self) -> None:
        cases = {
            "10.1000/example(foo)": "10.1000/example(foo)",
            "(doi: 10.1000/example(foo)).": "10.1000/example(foo)",
            "10.1000/example((foo))": "10.1000/example((foo))",
            "10.1000/example(foo)))": "10.1000/example(foo)",
            "10.1000/example[foo]": "10.1000/example[foo]",
            "10.1000/example{foo}": "10.1000/example{foo}",
            "10.1000/example[foo]]}": "10.1000/example[foo]",
            "https://doi.org/10.1000/example%28Foo%29": "10.1000/example(foo)",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_doi(raw), expected)

    def test_doi_links_escape_labels_and_encode_targets(self) -> None:
        self.assertEqual(
            doi_markdown("10.1000/example(foo)"),
            "[10.1000/example(foo)](https://doi.org/10.1000/example%28foo%29)",
        )
        self.assertEqual(
            doi_markdown("10.1000/example[foo]"),
            r"[10.1000/example\[foo\]](https://doi.org/10.1000/example%5Bfoo%5D)",
        )
        self.assertEqual(doi_url("10.1000/example%28foo%29"), "https://doi.org/10.1000/example%28foo%29")
        self.assertEqual(
            doi_latex("10.1000/example{foo}"),
            r"\href{https://doi.org/10.1000/example\%7Bfoo\%7D}{10.1000/example\{foo\}}",
        )

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

    def test_url_markdown_escapes_label_and_target_delimiters(self) -> None:
        self.assertEqual(
            url_markdown("https://example.test/a[part](one)"),
            r"[a\[part\](one)](https://example.test/a%5Bpart%5D%28one%29)",
        )


if __name__ == "__main__":
    unittest.main()
