from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from academic_clipboard.classifier import classify
from academic_clipboard.models import ClipboardItem

SCHEMA = """
CREATE TABLE IF NOT EXISTS clipboard_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    normalized_content TEXT NOT NULL,
    kind TEXT NOT NULL,
    subtype TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_copied_at TEXT NOT NULL DEFAULT '',
    copy_count INTEGER NOT NULL DEFAULT 1,
    pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
    tags TEXT NOT NULL DEFAULT '',
    custom_title INTEGER NOT NULL DEFAULT 0 CHECK (custom_title IN (0, 1)),
    media_path TEXT NOT NULL DEFAULT '',
    width INTEGER NOT NULL DEFAULT 0,
    height INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_clipboard_created ON clipboard_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clipboard_kind ON clipboard_items(kind);
CREATE INDEX IF NOT EXISTS idx_clipboard_pinned ON clipboard_items(pinned DESC, created_at DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _item(row: sqlite3.Row) -> ClipboardItem:
    return ClipboardItem(
        id=row["id"],
        content=row["content"],
        normalized_content=row["normalized_content"],
        kind=row["kind"],
        subtype=row["subtype"],
        title=row["title"],
        created_at=row["created_at"],
        last_copied_at=row["last_copied_at"],
        copy_count=row["copy_count"],
        pinned=bool(row["pinned"]),
        tags=row["tags"],
        media_path=row["media_path"],
        width=row["width"],
        height=row["height"],
    )


class ClipboardStore:
    def __init__(self, path: Path):
        self.path = path
        self.images_dir = path.parent / "images"
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(SCHEMA)
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(clipboard_items)").fetchall()
            }
            if "tags" not in columns:
                connection.execute("ALTER TABLE clipboard_items ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
            if "custom_title" not in columns:
                connection.execute(
                    "ALTER TABLE clipboard_items ADD COLUMN custom_title INTEGER NOT NULL DEFAULT 0"
                )
            for name, definition in (
                ("media_path", "TEXT NOT NULL DEFAULT ''"),
                ("width", "INTEGER NOT NULL DEFAULT 0"),
                ("height", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE clipboard_items ADD COLUMN {name} {definition}")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def add(self, content: str) -> ClipboardItem:
        detected = classify(content)
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        now = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO clipboard_items
                    (content, content_hash, normalized_content, kind, subtype, title, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    content = excluded.content,
                    normalized_content = excluded.normalized_content,
                    kind = excluded.kind,
                    subtype = excluded.subtype,
                    title = CASE clipboard_items.custom_title
                        WHEN 1 THEN clipboard_items.title ELSE excluded.title END,
                    created_at = excluded.created_at,
                    copy_count = clipboard_items.copy_count + 1
                """,
                (
                    content,
                    digest,
                    detected.normalized_content,
                    detected.kind,
                    detected.subtype,
                    detected.title,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM clipboard_items WHERE content_hash = ?", (digest,)
            ).fetchone()
        assert row is not None
        return _item(row)

    def add_image(self, png_bytes: bytes, width: int, height: int) -> ClipboardItem:
        if not png_bytes or width < 1 or height < 1:
            raise ValueError("image data and dimensions must be valid")
        digest = hashlib.sha256(png_bytes).hexdigest()
        content_hash = f"image:{digest}"
        relative_path = Path("images") / f"{digest}.png"
        media_path = self.path.parent / relative_path
        self.images_dir.mkdir(parents=True, exist_ok=True)
        if not media_path.exists():
            media_path.write_bytes(png_bytes)
        now = _now()
        description = f"[Image {width}×{height}]"
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO clipboard_items
                        (content, content_hash, normalized_content, kind, subtype, title, created_at,
                         media_path, width, height)
                    VALUES (?, ?, ?, 'image', 'screenshot', 'Screenshot / 截图', ?, ?, ?, ?)
                    ON CONFLICT(content_hash) DO UPDATE SET
                        created_at = excluded.created_at,
                        copy_count = clipboard_items.copy_count + 1,
                        media_path = excluded.media_path,
                        width = excluded.width,
                        height = excluded.height
                    """,
                    (
                        description,
                        content_hash,
                        description,
                        now,
                        relative_path.as_posix(),
                        width,
                        height,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM clipboard_items WHERE content_hash = ?", (content_hash,)
                ).fetchone()
        except Exception:
            with self._connection() as connection:
                referenced = connection.execute(
                    "SELECT 1 FROM clipboard_items WHERE media_path = ?", (relative_path.as_posix(),)
                ).fetchone()
            if referenced is None:
                media_path.unlink(missing_ok=True)
            raise
        assert row is not None
        return _item(row)

    def media_file(self, item: ClipboardItem) -> Path | None:
        if item.kind != "image" or not item.media_path:
            return None
        base = self.images_dir.resolve()
        candidate = (self.path.parent / item.media_path).resolve()
        if not candidate.is_relative_to(base):
            raise ValueError("image path points outside the local media directory")
        return candidate

    def list_items(self, search: str = "", kind: str = "all", limit: int = 500) -> list[ClipboardItem]:
        clauses: list[str] = []
        parameters: list[object] = []
        if search.strip():
            clauses.append(
                "(content LIKE ? OR normalized_content LIKE ? OR title LIKE ? OR subtype LIKE ? OR tags LIKE ?)"
            )
            term = f"%{search.strip()}%"
            parameters.extend([term, term, term, term, term])
        if kind and kind != "all":
            clauses.append("kind = ?")
            parameters.append(kind)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(limit, 5000)))
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM clipboard_items {where} ORDER BY pinned DESC, created_at DESC LIMIT ?",  # noqa: S608
                parameters,
            ).fetchall()
        return [_item(row) for row in rows]

    def get_many(self, identifiers: list[int]) -> list[ClipboardItem]:
        if not identifiers:
            return []
        placeholders = ",".join("?" for _ in identifiers)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM clipboard_items WHERE id IN ({placeholders})",  # noqa: S608
                identifiers,
            ).fetchall()
        indexed = {row["id"]: _item(row) for row in rows}
        return [indexed[identifier] for identifier in identifiers if identifier in indexed]

    def mark_copied(self, identifiers: list[int]) -> None:
        if not identifiers:
            return
        placeholders = ",".join("?" for _ in identifiers)
        with self._connection() as connection:
            connection.execute(
                f"UPDATE clipboard_items SET last_copied_at = ?, "  # noqa: S608
                f"copy_count = copy_count + 1 WHERE id IN ({placeholders})",
                [_now(), *identifiers],
            )

    def update(self, identifier: int, content: str, title: str, tags: str = "") -> ClipboardItem:
        existing = self.get_many([identifier])
        if existing and existing[0].kind == "image":
            raise ValueError("image items cannot be edited as text")
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("content cannot be empty")
        detected = classify(clean_content)
        digest = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
        clean_title = " ".join(title.split()) or detected.title
        clean_tags = ", ".join(dict.fromkeys(tag.strip() for tag in tags.split(",") if tag.strip()))
        try:
            with self._connection() as connection:
                cursor = connection.execute(
                    """
                    UPDATE clipboard_items SET
                        content = ?, content_hash = ?, normalized_content = ?, kind = ?, subtype = ?,
                        title = ?, tags = ?, custom_title = 1
                    WHERE id = ?
                    """,
                    (
                        clean_content,
                        digest,
                        detected.normalized_content,
                        detected.kind,
                        detected.subtype,
                        clean_title,
                        clean_tags,
                        identifier,
                    ),
                )
                if cursor.rowcount != 1:
                    raise KeyError(identifier)
                row = connection.execute(
                    "SELECT * FROM clipboard_items WHERE id = ?", (identifier,)
                ).fetchone()
        except sqlite3.IntegrityError as error:
            raise ValueError("another item already contains the same text") from error
        assert row is not None
        return _item(row)

    def toggle_pinned(self, identifiers: list[int]) -> None:
        if not identifiers:
            return
        placeholders = ",".join("?" for _ in identifiers)
        with self._connection() as connection:
            connection.execute(
                f"UPDATE clipboard_items SET pinned = CASE pinned WHEN 1 THEN 0 ELSE 1 END "  # noqa: S608
                f"WHERE id IN ({placeholders})",
                identifiers,
            )

    def delete(self, identifiers: list[int]) -> int:
        if not identifiers:
            return 0
        placeholders = ",".join("?" for _ in identifiers)
        with self._connection() as connection:
            media_paths = self._media_paths_for_ids(connection, identifiers)
            cursor = connection.execute(
                f"DELETE FROM clipboard_items WHERE id IN ({placeholders})",  # noqa: S608
                identifiers,
            )
        self._remove_media_files(media_paths)
        return cursor.rowcount

    def clear_unpinned(self) -> int:
        with self._connection() as connection:
            media_paths = [
                row["media_path"]
                for row in connection.execute(
                    "SELECT media_path FROM clipboard_items WHERE pinned = 0 AND media_path != ''"
                ).fetchall()
            ]
            cursor = connection.execute("DELETE FROM clipboard_items WHERE pinned = 0")
        self._remove_media_files(media_paths)
        return cursor.rowcount

    def clear_all(self) -> int:
        with self._connection() as connection:
            media_paths = [
                row["media_path"]
                for row in connection.execute(
                    "SELECT media_path FROM clipboard_items WHERE media_path != ''"
                ).fetchall()
            ]
            cursor = connection.execute("DELETE FROM clipboard_items")
        self._remove_media_files(media_paths)
        return cursor.rowcount

    def count(self) -> int:
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM clipboard_items").fetchone()[0])

    def prune(self, max_items: int, retention_days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))).isoformat(
            timespec="seconds"
        )
        with self._connection() as connection:
            expired_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM clipboard_items WHERE pinned = 0 AND created_at < ?", (cutoff,)
                ).fetchall()
            ]
            media_paths = self._media_paths_for_ids(connection, expired_ids)
            expired = connection.execute(
                "DELETE FROM clipboard_items WHERE pinned = 0 AND created_at < ?", (cutoff,)
            ).rowcount
            overflow_ids = [
                row["id"]
                for row in connection.execute(
                    """
                    SELECT id FROM clipboard_items
                    WHERE pinned = 0 AND id NOT IN (
                        SELECT id FROM clipboard_items WHERE pinned = 0
                        ORDER BY created_at DESC LIMIT ?
                    )
                    """,
                    (max(1, max_items),),
                ).fetchall()
            ]
            media_paths.extend(self._media_paths_for_ids(connection, overflow_ids))
            overflow = connection.execute(
                """
                DELETE FROM clipboard_items
                WHERE pinned = 0 AND id NOT IN (
                    SELECT id FROM clipboard_items WHERE pinned = 0 ORDER BY created_at DESC LIMIT ?
                )
                """,
                (max(1, max_items),),
            ).rowcount
        self._remove_media_files(media_paths)
        return expired + overflow

    def _media_paths_for_ids(self, connection: sqlite3.Connection, identifiers: list[int]) -> list[str]:
        if not identifiers:
            return []
        placeholders = ",".join("?" for _ in identifiers)
        rows = connection.execute(
            f"SELECT media_path FROM clipboard_items "  # noqa: S608
            f"WHERE id IN ({placeholders}) AND media_path != ''",
            identifiers,
        ).fetchall()
        return [row["media_path"] for row in rows]

    def _remove_media_files(self, media_paths: list[str]) -> None:
        base = self.images_dir.resolve()
        for relative_path in set(media_paths):
            candidate = (self.path.parent / relative_path).resolve()
            if candidate.is_relative_to(base):
                candidate.unlink(missing_ok=True)

    def export_json(self, path: Path) -> None:
        rows = self.list_items(limit=5000)
        payload = [
            {
                "id": item.id,
                "kind": item.kind,
                "subtype": item.subtype,
                "title": item.title,
                "content": item.content,
                "normalized_content": item.normalized_content,
                "created_at": item.created_at,
                "last_copied_at": item.last_copied_at,
                "copy_count": item.copy_count,
                "pinned": item.pinned,
                "tags": item.tags,
                "media_path": item.media_path,
                "width": item.width,
                "height": item.height,
            }
            for item in rows
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def export_markdown(self, path: Path) -> None:
        rows = self.list_items(limit=5000)
        lines = ["# Academic Clipboard export", ""]
        for item in rows:
            lines.extend(
                [
                    f"## {item.title or item.kind}",
                    "",
                    f"- Type: `{item.kind}/{item.subtype}`",
                    f"- Captured: {item.created_at}",
                    f"- Pinned: {'yes' if item.pinned else 'no'}",
                    f"- Tags: {item.tags or '-'}",
                    *(
                        [
                            f"- Image: `{item.media_path}`",
                            f"- Dimensions: {item.width}×{item.height}",
                        ]
                        if item.kind == "image"
                        else []
                    ),
                    "",
                    item.normalized_content,
                    "",
                ]
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
