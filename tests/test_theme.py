import unittest
from unittest.mock import patch

from academic_clipboard.i18n import tr
from academic_clipboard.theme import DARK, LIGHT, resolve_palette


class ThemeTests(unittest.TestCase):
    def test_explicit_themes_are_deterministic(self) -> None:
        self.assertIs(resolve_palette("light"), LIGHT)
        self.assertIs(resolve_palette("dark"), DARK)

    def test_windows_chinese_locale_uses_one_ui_language(self) -> None:
        with (
            patch("academic_clipboard.i18n.sys.platform", "win32"),
            patch(
                "academic_clipboard.i18n.locale.getlocale", return_value=("Chinese (Simplified)_China", "936")
            ),
        ):
            self.assertEqual(tr("复制", "Copy"), "复制")

    def test_mac_uses_system_preferred_language(self) -> None:
        with (
            patch("academic_clipboard.i18n.sys.platform", "darwin"),
            patch("academic_clipboard.i18n._mac_language", return_value="zh-Hans-CN"),
        ):
            self.assertEqual(tr("复制", "Copy"), "复制")


if __name__ == "__main__":
    unittest.main()
