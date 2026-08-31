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
    max_characters: int = 100_000
    poll_milliseconds: int = 650
    join_separator: str = "\n\n"
    capture_sensitive: bool = False
    always_on_top: bool = True
    compact_mode: bool = True

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        allowed = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
