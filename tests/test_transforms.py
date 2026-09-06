import tempfile
import unittest
from pathlib import Path

from academic_clipboard.storage import ClipboardStore
from academic_clipboard.transforms import (
    available_transforms,
    bibtex_fields,
    bibtex_reference,
    latex_table,
    markdown_table,
)


class TransformTests(unittest.TestCase):
    def test_tabular_text_converts_to_markdown_and_latex(self) -> None:
        source = "Variable\tMean\tSE\nTreatment\t1.25\t0.10"
        self.assertIn("| Variable | Mean | SE |", markdown_table(source))
        latex = latex_table(source)
        self.assertIn(r"\begin{tabular}{lll}", latex)
        self.assertIn(r"Treatment & 1.25 & 0.10 \\", latex)

    def test_bibtex_fields_and_reference_drafts(self) -> None:
        source = (
            "@article{key, author={Doe, Jane and Roe, John}, title={A Result}, "
            "journal={Journal of Tests}, year={2025}, volume={4}, number={2}, "
            "pages={10--20}, doi={10.1000/test}}"
        )
        self.assertEqual(bibtex_fields(source)["title"], "A Result")
        self.assertIn("A Result[J]", bibtex_reference(source, "gbt"))
        self.assertIn("https://doi.org/10.1000/test", bibtex_reference(source, "apa"))

    def test_doi_has_url_markdown_and_latex_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            item = ClipboardStore(Path(directory) / "clips.db").add("10.1000/action")
        actions = {action.key: action.value for action in available_transforms(item)}
        self.assertEqual(actions["doi-url"], "https://doi.org/10.1000/action")
        self.assertIn("[10.1000/action]", actions["markdown"])
        self.assertIn(r"\href", actions["latex"])


if __name__ == "__main__":
    unittest.main()
