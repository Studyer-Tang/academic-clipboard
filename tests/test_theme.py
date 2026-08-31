import unittest

from academic_clipboard.theme import DARK, LIGHT, resolve_palette


class ThemeTests(unittest.TestCase):
    def test_explicit_themes_are_deterministic(self) -> None:
        self.assertIs(resolve_palette("light"), LIGHT)
        self.assertIs(resolve_palette("dark"), DARK)


if __name__ == "__main__":
    unittest.main()
