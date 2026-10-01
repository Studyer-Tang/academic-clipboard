from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def application_dir() -> Path:
    override = os.environ.get("ACADEMIC_CLIPBOARD_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "AcademicClipboard"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AcademicClipboard"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "academic-clipboard"


@dataclass(slots=True)
class Settings:
    max_items: int = 2000
    retention_days: int = 90
    max_storage_mb: int = 256
    max_characters: int = 100_000
    poll_milliseconds: int = 650
    join_separator: str = "\n\n"
    capture_sensitive: bool = False
    always_on_top: bool = True
    compact_mode: bool = True
    auto_hide_after_copy: bool = True
    global_hotkey: str = "Ctrl+Alt+V"
    theme: str = "system"

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        result = cls()
        if not isinstance(data, dict):
            return result
        for field in fields(cls):
            default = getattr(result, field.name)
            value = data.get(field.name, default)
            if type(value) is type(default):
                setattr(result, field.name, value)
        result.max_items = min(10000, max(10, result.max_items))
        result.retention_days = min(3650, max(1, result.retention_days))
        result.max_storage_mb = min(4096, max(16, result.max_storage_mb))
        result.max_characters = min(1_000_000, max(100, result.max_characters))
        result.poll_milliseconds = min(5000, max(250, result.poll_milliseconds))
        if result.theme not in {"system", "light", "dark"}:
            result.theme = "system"
        return result

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
