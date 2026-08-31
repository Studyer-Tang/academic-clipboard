import json
import tempfile
import unittest
from pathlib import Path

from academic_clipboard.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_floating_window_is_the_default(self) -> None:
        settings = Settings()
        self.assertTrue(settings.compact_mode)
        self.assertTrue(settings.always_on_top)

    def test_round_trip_and_forward_compatible_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            settings = Settings(compact_mode=False, always_on_top=False)
            settings.save(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["future_option"] = True
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = Settings.load(path)
            self.assertFalse(loaded.compact_mode)
            self.assertFalse(loaded.always_on_top)


if __name__ == "__main__":
    unittest.main()
