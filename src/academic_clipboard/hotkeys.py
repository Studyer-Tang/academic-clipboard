from __future__ import annotations

import ctypes
import sys
import threading
from collections.abc import Callable
from ctypes import wintypes

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
HOTKEY_ID = 0xAC01

MODIFIERS = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
}

SPECIAL_KEYS = {
    "space": 0x20,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "escape": 0x1B,
}


def parse_hotkey(value: str) -> tuple[int, int]:
    parts = [part.strip().casefold() for part in value.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("hotkey must include a modifier and a key")
    modifiers = 0
    key_name = parts[-1]
    for part in parts[:-1]:
        try:
            modifiers |= MODIFIERS[part]
        except KeyError as error:
            raise ValueError(f"unknown modifier: {part}") from error
    if not modifiers:
        raise ValueError("hotkey must include Ctrl, Alt, Shift, or Win")
    if len(key_name) == 1 and key_name.isalnum():
        virtual_key = ord(key_name.upper())
    elif key_name in SPECIAL_KEYS:
        virtual_key = SPECIAL_KEYS[key_name]
    elif key_name.startswith("f") and key_name[1:].isdigit() and 1 <= int(key_name[1:]) <= 24:
        virtual_key = 0x70 + int(key_name[1:]) - 1
    else:
        raise ValueError(f"unsupported key: {key_name}")
    return modifiers | MOD_NOREPEAT, virtual_key


class GlobalHotkey:
    def __init__(self, specification: str, callback: Callable[[], None]):
        self.specification = specification
        self.callback = callback
        self.thread: threading.Thread | None = None
        self.thread_id = 0
        self.registered = False
        self.error = ""
        self.ready = threading.Event()

    def start(self) -> tuple[bool, str]:
        if sys.platform != "win32":
            return False, "global hotkeys are currently supported on Windows"
        try:
            modifiers, virtual_key = parse_hotkey(self.specification)
        except ValueError as error:
            return False, str(error)
        self.thread = threading.Thread(
            target=self._run,
            args=(modifiers, virtual_key),
            name="AcademicClipboardHotkey",
            daemon=True,
        )
        self.thread.start()
        self.ready.wait(timeout=2)
        return self.registered, self.error

    def _run(self, modifiers: int, virtual_key: int) -> None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.UnregisterHotKey.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = (
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        )
        user32.GetMessageW.restype = wintypes.BOOL
        self.thread_id = int(kernel32.GetCurrentThreadId())
        if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, virtual_key):
            self.error = f"could not register {self.specification} (Windows error {ctypes.get_last_error()})"
            self.ready.set()
            return
        self.registered = True
        self.ready.set()
        message = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY and message.wParam == HOTKEY_ID:
                    self.callback()
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            self.registered = False

    def stop(self) -> None:
        if self.thread_id and self.thread and self.thread.is_alive():
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            self.thread.join(timeout=2)
        self.thread = None
        self.thread_id = 0
