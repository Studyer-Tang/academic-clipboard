from __future__ import annotations

import locale


def uses_chinese() -> bool:
    language = (locale.getlocale()[0] or "").casefold()
    return language.startswith("zh") or "chinese" in language


def tr(chinese: str, english: str) -> str:
    """Return one concise UI language instead of displaying both at once."""
    return chinese if uses_chinese() else english
