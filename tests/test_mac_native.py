"""Real Cocoa round trips on a private pasteboard; never read the user's clipboard."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


@unittest.skipUnless(sys.platform == "darwin", "macOS native pasteboard")
class MacPasteboardTests(unittest.TestCase):
    def test_text_image_and_privacy_roundtrip(self):
        from AppKit import NSPasteboard
        from PIL import Image

        from academic_clipboard.clipboard import ClipboardState
        from academic_clipboard.images import copy_image_to_clipboard, read_clipboard_image

        board = NSPasteboard.pasteboardWithUniqueName()
        try:
            with patch("AppKit.NSPasteboard", Mock(generalPasteboard=lambda: board)):
                state = ClipboardState()
                state.set_text("Synthetic research sample 中文")
                self.assertEqual(state.text(), "Synthetic research sample 中文")
                self.assertTrue(state.changed())
                self.assertFalse(state.changed())
                board.setString_forType_("1", "org.nspasteboard.ConcealedType")
                self.assertTrue(state.private())
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "sample.png"
                    Image.new("RGB", (23, 17), "blue").save(path)
                    copy_image_to_clipboard(path)
                    image = read_clipboard_image()
                self.assertIsNotNone(image)
                self.assertEqual((image.width, image.height), (23, 17))
                self.assertFalse(state.private())
        finally:
            board.releaseGlobally()
