from __future__ import annotations

import locale
import sys
from functools import lru_cache


@lru_cache(maxsize=1)
def _mac_language() -> str:
    from Foundation import NSLocale

    languages = NSLocale.preferredLanguages()
    return str(languages[0]) if languages else "en"


def uses_chinese() -> bool:
    language = (_mac_language() if sys.platform == "darwin" else locale.getlocale()[0] or "").casefold()
    return language.startswith("zh") or "chinese" in language


def tr(chinese: str, english: str) -> str:
    """Return one concise UI language instead of displaying both at once."""
    return chinese if uses_chinese() else english
