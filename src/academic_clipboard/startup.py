from __future__ import annotations

import subprocess
import sys
from contextlib import suppress
from pathlib import Path

APP_NAME = "AcademicClipboard"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def background_arguments(executable: Path | None = None, frozen: bool | None = None) -> list[str]:
    executable = executable or Path(sys.executable)
    frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if frozen:
        return [str(executable), "run", "--hidden"]
    pythonw = executable.with_name("pythonw.exe") if sys.platform == "win32" else executable
    if sys.platform == "win32" and not pythonw.exists():
        pythonw = executable
    return [str(pythonw), "-m", "academic_clipboard", "run", "--hidden"]


def background_command() -> str:
    return subprocess.list2cmdline(background_arguments())


def launch_background() -> None:
    if sys.platform != "win32":
        raise OSError("background launch is currently supported on Windows")
    subprocess.Popen(
        background_arguments(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
        ),
    )


def set_startup(enabled: bool) -> None:
    if sys.platform != "win32":
        raise OSError("startup registration is currently supported on Windows")
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, background_command())
        else:
            with suppress(FileNotFoundError):
                winreg.DeleteValue(key, APP_NAME)


def startup_command() -> str:
    if sys.platform != "win32":
        return ""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, APP_NAME)
            return str(value)
    except FileNotFoundError:
        return ""
