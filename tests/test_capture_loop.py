import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from academic_clipboard.app import AcademicClipboardApp


class CaptureLoopTests(unittest.TestCase):
    def app(self):
        app = AcademicClipboardApp.__new__(AcademicClipboardApp)
        app.root = Mock()
        app.clipboard = Mock()
        app.clipboard.private.return_value = False
        app.clipboard.changed.return_value = True
        app.settings = SimpleNamespace(poll_milliseconds=650)
        app.status_var = Mock()
        app.shutting_down = False
        app.capture_enabled = True
        return app

    def test_unchanged_paused_and_private_clipboards_do_not_read_payloads(self):
        for changed, enabled, private in ((False, True, False), (True, False, False), (True, True, True)):
            with self.subTest(changed=changed, enabled=enabled, private=private):
                app = self.app()
                app.capture_enabled = enabled
                app.clipboard.changed.return_value = changed
                app.clipboard.private.return_value = private
                app._capture_clipboard = Mock()
                app._poll_clipboard()
                app._capture_clipboard.assert_not_called()
                app.root.after.assert_called_once()

    def test_temporary_failure_reschedules_and_retries(self):
        app = self.app()
        app._capture_clipboard = Mock(side_effect=OSError("busy"))
        app._poll_clipboard()
        app.clipboard.forget.assert_called_once()
        app.root.after.assert_called_once()

    def test_oversized_image_is_not_retried_forever(self):
        app = self.app()
        app._capture_clipboard = Mock(side_effect=ValueError("too large"))
        app._poll_clipboard()
        app.clipboard.forget.assert_not_called()
        app.root.after.assert_called_once()

    def test_racing_copy_does_not_save_mixed_snapshot(self):
        app = self.app()
        app.clipboard.sequence.side_effect = [1, 2]
        app._read_clipboard = Mock(return_value="Synthetic text")
        app._capture = Mock()
        app._capture_clipboard()
        app._capture.assert_not_called()
        app.clipboard.forget.assert_called_once()

    def test_copy_back_does_not_suppress_an_unrelated_screenshot(self):
        app = self.app()
        app.last_image_hash = "own-copy"
        app._read_clipboard = Mock(return_value="")
        app._capture_image = Mock()
        screenshot = SimpleNamespace(digest="new-copy")
        with patch("academic_clipboard.app.read_clipboard_image", return_value=screenshot):
            app._capture_clipboard()
        app._capture_image.assert_called_once_with(screenshot, force=False)
