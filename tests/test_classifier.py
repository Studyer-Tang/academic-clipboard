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

    def test_bibtex_containing_a_doi_is_still_bibtex(self) -> None:
        raw = "@article(demo, title={A Study}, doi={10.1000/example(foo)}, year=2025)"
        result = classify(raw)
        self.assertEqual((result.kind, result.title), ("bibtex", "demo"))
        self.assertIn("doi = {10.1000/example(foo)},", result.normalized_content)

    def test_chinese_research_titles_have_note_templates(self) -> None:
        titles = (
            "基于深度学习的多模态大模型推理与优化方法研究",
            "高维随机矩阵的谱分布理论与渐近性质分析",
            "基于 BERT 的中文文本分类模型与方法研究",
        )
        for raw in titles:
            with self.subTest(raw=raw):
                result = classify(raw)
                self.assertEqual((result.kind, result.subtype), ("title", "paper-title"))
                self.assertTrue(result.normalized_content.startswith(f"# {raw}\n"))

    def test_chinese_short_notes_and_prose_remain_text(self) -> None:
        notes = (
            "今天学习了新的方法",
            "优化模型",
            "明天再继续阅读这一篇论文的第三章",
            "这个模型的效果不错，明天可以继续研究",
            "基于深度学习的方法研究。",
            "第一段介绍了研究方法\n第二段说明结果",
        )
        for raw in notes:
            with self.subTest(raw=raw):
                self.assertEqual(classify(raw).kind, "text")

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

    def test_formula_and_table(self) -> None:
        formula = classify(r"\frac{\beta_1}{\sqrt{n}}")
        self.assertEqual((formula.kind, formula.subtype), ("formula", "latex"))
        table = classify("Variable\tMean\nTreatment\t1.25")
        self.assertEqual((table.kind, table.subtype), ("table", "tab-separated"))
        self.assertIn("| Variable | Mean |", table.normalized_content)


if __name__ == "__main__":
    unittest.main()
