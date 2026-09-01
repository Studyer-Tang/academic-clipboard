from __future__ import annotations

import ctypes
import hashlib
import io
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageGrab


@dataclass(frozen=True, slots=True)
class ClipboardImage:
    png_bytes: bytes
    width: int
    height: int
    digest: str


def encode_png(image: Image.Image) -> ClipboardImage:
    """Convert a clipboard bitmap to a deterministic, portable PNG payload."""
    # A Windows DIB round-trip can drop an opaque alpha channel. Always using
    # RGBA keeps the same visible screenshot stable across capture and copy-back.
    normalized = image.convert("RGBA")
    output = io.BytesIO()
    normalized.save(output, format="PNG")
    payload = output.getvalue()
    return ClipboardImage(
        png_bytes=payload,
        width=normalized.width,
        height=normalized.height,
        digest=hashlib.sha256(payload).hexdigest(),
    )


def read_clipboard_image() -> ClipboardImage | None:
    """Read an actual clipboard bitmap, ignoring lists of copied file paths."""
    try:
        value = ImageGrab.grabclipboard()
    except (OSError, NotImplementedError):
        return None
    if not isinstance(value, Image.Image):
        return None
    return encode_png(value)


def _dib_bytes(path: Path) -> bytes:
    with Image.open(path) as image:
        output = io.BytesIO()
        image.convert("RGB").save(output, format="BMP")
    return output.getvalue()[14:]


def copy_image_to_clipboard(path: Path) -> None:
    """Place a saved image on the Windows clipboard as a device-independent bitmap."""
    if sys.platform != "win32":
        raise OSError("copying images is currently supported on Windows only")

    payload = _dib_bytes(path)
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_int
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_int
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    opened = False
    for _attempt in range(10):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.03)
    if not opened:
        raise OSError("the Windows clipboard is busy")

    handle = None
    try:
        if not user32.EmptyClipboard():
            raise OSError("could not clear the Windows clipboard")
        handle = kernel32.GlobalAlloc(0x0002, len(payload))  # GMEM_MOVEABLE
        if not handle:
            raise MemoryError("could not allocate clipboard memory")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise MemoryError("could not lock clipboard memory")
        try:
            ctypes.memmove(pointer, payload, len(payload))
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(8, ctypes.c_void_p(handle)):  # CF_DIB
            raise OSError("could not set clipboard image data")
        handle = None  # Windows owns the memory after SetClipboardData succeeds.
    finally:
        user32.CloseClipboard()
        if handle:
            kernel32.GlobalFree(handle)
