import unittest

from academic_clipboard.classifier import classify


class ClassifierTests(unittest.TestCase):
    def test_research_types(self) -> None:
        cases = {
            "10.1038/s41586-020-2649-2": ("doi", "paper"),
            "https://arxiv.org/abs/2401.00001": ("url", "paper"),
            "https://docs.python.org/3/library/tkinter.html": ("url", "docs"),
            "https://zenodo.org/records/123": ("url", "dataset"),
            "https://github.com/openai/openai-python": ("url", "github"),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                result = classify(value)
                self.assertEqual((result.kind, result.subtype), expected)

    def test_bibtex(self) -> None:
        result = classify("@article{demo, title={A Study}, year={2025}}")
        self.assertEqual((result.kind, result.subtype, result.title), ("bibtex", "citation", "demo"))

    def test_code_languages(self) -> None:
        cases = {
            "def answer():\n    return 42": "python",
            "const value = () => {\n  return 42;\n};": "javascript",
            "SELECT id, title\nFROM papers;": "sql",
        }
        for value, language in cases.items():
            with self.subTest(language=language):
                result = classify(value)
                self.assertEqual((result.kind, result.subtype), ("code", language))

    def test_title_and_plain_text(self) -> None:
        title = classify("The Limited Virtue of Complexity in a Noisy World")
        self.assertEqual((title.kind, title.subtype), ("title", "paper-title"))
        paragraph = classify("This is a complete sentence about a result.")
        self.assertEqual((paragraph.kind, paragraph.subtype), ("text", "plain"))


if __name__ == "__main__":
    unittest.main()
