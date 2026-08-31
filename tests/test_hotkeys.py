import unittest

from academic_clipboard.hotkeys import MOD_ALT, MOD_CONTROL, MOD_NOREPEAT, parse_hotkey


class HotkeyTests(unittest.TestCase):
    def test_parses_letters_space_and_function_keys(self) -> None:
        modifiers, key = parse_hotkey("Ctrl+Alt+V")
        self.assertEqual(modifiers, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT)
        self.assertEqual(key, ord("V"))
        self.assertEqual(parse_hotkey("Ctrl+Shift+Space")[1], 0x20)
        self.assertEqual(parse_hotkey("Alt+F12")[1], 0x7B)

    def test_rejects_invalid_hotkeys(self) -> None:
        for value in ("V", "Ctrl+Mystery", "Hyper+V"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_hotkey(value)


if __name__ == "__main__":
    unittest.main()
