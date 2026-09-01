import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from academic_clipboard.images import _dib_bytes, encode_png, read_clipboard_image


class ImageClipboardTests(unittest.TestCase):
    def test_encode_png_is_stable_and_preserves_dimensions(self) -> None:
        source = Image.new("RGB", (27, 13), "royalblue")
        first = encode_png(source)
        second = encode_png(source)
        self.assertEqual((first.width, first.height), (27, 13))
        self.assertEqual(first.png_bytes, second.png_bytes)
        self.assertEqual(first.digest, second.digest)

    def test_opaque_rgb_and_rgba_images_have_the_same_digest(self) -> None:
        rgb = Image.new("RGB", (17, 9), (10, 20, 30))
        rgba = Image.new("RGBA", (17, 9), (10, 20, 30, 255))
        self.assertEqual(encode_png(rgb).digest, encode_png(rgba).digest)

    @patch("academic_clipboard.images.ImageGrab.grabclipboard")
    def test_read_clipboard_image_ignores_copied_files(self, grabclipboard) -> None:
        grabclipboard.return_value = [Path("paper.pdf")]
        self.assertIsNone(read_clipboard_image())

    @patch("academic_clipboard.images.ImageGrab.grabclipboard")
    def test_read_clipboard_image_accepts_bitmap(self, grabclipboard) -> None:
        grabclipboard.return_value = Image.new("RGBA", (11, 7), (10, 20, 30, 128))
        captured = read_clipboard_image()
        self.assertIsNotNone(captured)
        assert captured is not None
        self.assertEqual((captured.width, captured.height), (11, 7))

    def test_saved_png_can_be_encoded_as_windows_dib(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "test.png"
            Image.new("RGB", (8, 6), "white").save(path)
            dib = _dib_bytes(path)
        self.assertEqual(int.from_bytes(dib[:4], "little"), 40)
        self.assertGreater(len(dib), 40)


if __name__ == "__main__":
    unittest.main()
