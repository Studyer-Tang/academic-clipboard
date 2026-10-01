from __future__ import annotations

import ctypes
import hashlib
import sys
from ctypes import wintypes

from academic_clipboard.settings import application_dir

ERROR_ALREADY_EXISTS = 183


class SingleInstance:
    def __init__(self, name: str = "Local\\AcademicClipboard"):
        self.handle: int | None = None
        self._kernel32 = None
        self._lock_file = None
        self.already_running = False
        if sys.platform != "win32":
            import fcntl

            home = application_dir()
            home.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(name.encode()).hexdigest()[:16]
            self._lock_file = (home / f"instance-{digest}.lock").open("a")
            try:
                fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                self.already_running = True
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            raise OSError(ctypes.get_last_error(), "could not create application mutex")
        self._kernel32 = kernel32
        self.handle = int(handle)
        self.already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS

    def close(self) -> None:
        if self._lock_file is not None:
            self._lock_file.close()
            self._lock_file = None
        if self.handle is not None and self._kernel32 is not None:
            self._kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self) -> "SingleInstance":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def notify_already_running() -> None:
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(
            None,
            "Academic Clipboard is already running in the system tray.\n"
            "Academic Clipboard 已在系统托盘中运行。",
            "Academic Clipboard",
            0x40,
        )
