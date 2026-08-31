from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassifiedClip:
    kind: str
    subtype: str
    title: str
    normalized_content: str


@dataclass(frozen=True, slots=True)
class ClipboardItem:
    id: int
    content: str
    normalized_content: str
    kind: str
    subtype: str
    title: str
    created_at: str
    last_copied_at: str
    copy_count: int
    pinned: bool
    tags: str = ""
