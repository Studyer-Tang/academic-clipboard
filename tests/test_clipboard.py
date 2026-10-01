import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from academic_clipboard.clipboard import ClipboardState
from academic_clipboard.settings import Settings
from academic_clipboard.single_instance import SingleInstance


class ClipboardTests(unittest.TestCase):
    def state(self):
        with patch("academic_clipboard.clipboard.sys.platform", "linux"):
            return ClipboardState()

    def test_unchanged_clipboard_does_not_trigger_payload_reads(self):
        state = self.state()
        with patch.object(state, "sequence", side_effect=[1, 1, 2, 2]):
            self.assertEqual([state.changed() for _ in range(4)], [True, False, True, False])

    def test_unknown_sequence_falls_back_to_content_comparison(self):
        state = self.state()
        self.assertTrue(state.changed())
        self.assertTrue(state.changed())

    def test_private_markers_are_respected_even_without_password_pattern(self):
        state = self.state()
        state._pasteboard = Mock()
        state._pasteboard.types.return_value = ["public.utf8-plain-text", "org.nspasteboard.ConcealedType"]
        self.assertTrue(state.private())
        state._pasteboard.types.return_value = ["public.utf8-plain-text"]
        self.assertFalse(state.private())

    def test_invalid_settings_do_not_crash_or_busy_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            for text in ("{broken", "[]", "null"):
                path.write_text(text)
                self.assertEqual(Settings.load(path), Settings())
            path.write_text('{"poll_milliseconds": -1, "max_items": "200", "capture_sensitive": "false"}')
            settings = Settings.load(path)
            self.assertEqual(settings.poll_milliseconds, 250)
            self.assertEqual(settings.max_items, 2000)
            self.assertFalse(settings.capture_sensitive)

    @unittest.skipIf(__import__("sys").platform == "win32", "POSIX file lock")
    def test_single_instance_released_on_close(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict("os.environ", ACADEMIC_CLIPBOARD_HOME=directory),
        ):
            first, second = SingleInstance(), SingleInstance()
            try:
                self.assertFalse(first.already_running)
                self.assertTrue(second.already_running)
            finally:
                second.close()
                first.close()
            with SingleInstance() as third:
                self.assertFalse(third.already_running)
