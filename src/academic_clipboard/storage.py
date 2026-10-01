from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
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
    height INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT '',
    locator TEXT NOT NULL DEFAULT '',
    project TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''
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
        source=row["source"],
        locator=row["locator"],
        project=row["project"],
        note=row["note"],
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
                ("source", "TEXT NOT NULL DEFAULT ''"),
                ("locator", "TEXT NOT NULL DEFAULT ''"),
                ("project", "TEXT NOT NULL DEFAULT ''"),
                ("note", "TEXT NOT NULL DEFAULT ''"),
            ):
                if name not in columns:
                    connection.execute(f"ALTER TABLE clipboard_items ADD COLUMN {name} {definition}")
            if "payload_bytes" not in columns:
                connection.execute(
                    "ALTER TABLE clipboard_items ADD COLUMN payload_bytes INTEGER NOT NULL DEFAULT 0"
                )
                connection.execute(
                    "UPDATE clipboard_items SET payload_bytes = length(CAST(content AS BLOB)) "
                    "+ length(CAST(normalized_content AS BLOB))"
                )
                for row in connection.execute(
                    "SELECT id, media_path FROM clipboard_items WHERE media_path != ''"
                ):
                    path = (self.path.parent / row["media_path"]).resolve()
                    if path.is_relative_to(self.images_dir.resolve()) and path.is_file():
                        connection.execute(
                            "UPDATE clipboard_items SET payload_bytes = ? WHERE id = ?",
                            (path.stat().st_size, row["id"]),
                        )

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
                    (content, content_hash, normalized_content, kind, subtype, title, created_at, payload_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    content = excluded.content,
                    normalized_content = excluded.normalized_content,
                    kind = excluded.kind,
                    subtype = excluded.subtype,
                    title = CASE clipboard_items.custom_title
                        WHEN 1 THEN clipboard_items.title ELSE excluded.title END,
                    created_at = excluded.created_at,
                    copy_count = clipboard_items.copy_count + 1,
                    payload_bytes = excluded.payload_bytes
                """,
                (
                    content,
                    digest,
                    detected.normalized_content,
                    detected.kind,
                    detected.subtype,
                    detected.title,
                    now,
                    len(content.encode("utf-8")) + len(detected.normalized_content.encode("utf-8")),
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
                         media_path, width, height, payload_bytes)
                    VALUES (?, ?, ?, 'image', 'screenshot', 'Screenshot / 截图', ?, ?, ?, ?, ?)
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
                        len(png_bytes),
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

    def list_items(
        self, search: str = "", kind: str = "all", limit: int = 500, previews: bool = False
    ) -> list[ClipboardItem]:
        clauses: list[str] = []
        parameters: list[object] = []
        if search.strip():
            clauses.append(
                "(content LIKE ? ESCAPE '\\' OR normalized_content LIKE ? ESCAPE '\\' "
                "OR title LIKE ? ESCAPE '\\' OR subtype LIKE ? ESCAPE '\\' "
                "OR tags LIKE ? ESCAPE '\\' OR source LIKE ? ESCAPE '\\' "
                "OR locator LIKE ? ESCAPE '\\' OR project LIKE ? ESCAPE '\\' OR note LIKE ? ESCAPE '\\')"
            )
            term = "%" + search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            parameters.extend([term] * 9)
        if kind and kind != "all":
            clauses.append("kind = ?")
            parameters.append(kind)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(limit, 5000)))
        columns = "*"
        if previews:
            columns = (
                "id, substr(content,1,240) AS content, '' AS normalized_content, kind, subtype, "
                "title, created_at, last_copied_at, copy_count, pinned, tags, media_path, width, "
                "height, source, locator, project, '' AS note"
            )
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT {columns} FROM clipboard_items {where} ORDER BY pinned DESC, created_at DESC, id DESC LIMIT ?",  # noqa: S608
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

    def update(
        self,
        identifier: int,
        content: str,
        title: str,
        tags: str = "",
        source: str = "",
        locator: str = "",
        project: str = "",
        note: str = "",
    ) -> ClipboardItem:
        existing = self.get_many([identifier])
        if existing and existing[0].kind == "image":
            raise ValueError("image items cannot be edited as text")
        clean_content = content
        if not clean_content.strip():
            raise ValueError("content cannot be empty")
        detected = classify(clean_content)
        digest = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
        clean_title = " ".join(title.split()) or detected.title
        clean_tags = ", ".join(dict.fromkeys(tag.strip() for tag in tags.split(",") if tag.strip()))
        clean_source = " ".join(source.split())
        clean_locator = " ".join(locator.split())
        clean_project = " ".join(project.split())
        clean_note = note.strip()
        try:
            with self._connection() as connection:
                cursor = connection.execute(
                    """
                    UPDATE clipboard_items SET
                        content = ?, content_hash = ?, normalized_content = ?, kind = ?, subtype = ?,
                        title = ?, tags = ?, source = ?, locator = ?, project = ?, note = ?,
                        custom_title = 1, payload_bytes = ?
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
                        clean_source,
                        clean_locator,
                        clean_project,
                        clean_note,
                        len(clean_content.encode("utf-8")) + len(detected.normalized_content.encode("utf-8")),
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

    def update_context(
        self,
        identifier: int,
        title: str,
        tags: str = "",
        source: str = "",
        locator: str = "",
        project: str = "",
        note: str = "",
    ) -> ClipboardItem:
        """Update research metadata without reclassifying or replacing the captured payload."""
        clean_title = " ".join(title.split())
        clean_tags = ", ".join(dict.fromkeys(tag.strip() for tag in tags.split(",") if tag.strip()))
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE clipboard_items SET
                    title = CASE WHEN ? = '' THEN title ELSE ? END,
                    tags = ?, source = ?, locator = ?, project = ?, note = ?, custom_title = 1
                WHERE id = ?
                """,
                (
                    clean_title,
                    clean_title,
                    clean_tags,
                    " ".join(source.split()),
                    " ".join(locator.split()),
                    " ".join(project.split()),
                    note.strip(),
                    identifier,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(identifier)
            row = connection.execute("SELECT * FROM clipboard_items WHERE id = ?", (identifier,)).fetchone()
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

    def prune(self, max_items: int, retention_days: int, max_storage_mb: int = 256) -> int:
        """Bound unpinned payloads; pinned research notes are never silently removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))).isoformat(
            timespec="seconds"
        )
        budget = max(1, max_storage_mb) * 1024 * 1024
        used = kept = 0
        identifiers = []
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT id, created_at, payload_bytes FROM clipboard_items WHERE pinned = 0 "
                "ORDER BY created_at DESC, id DESC"
            )
            for row in rows:
                size = row["payload_bytes"]
                if row["created_at"] < cutoff or kept >= max(1, max_items) or used + size > budget:
                    identifiers.append(row["id"])
                else:
                    used += size
                    kept += 1
        # Keep parameter counts below SQLite's older 999-variable limit.
        return sum(self.delete(identifiers[start : start + 500]) for start in range(0, len(identifiers), 500))

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

    def iter_items(self) -> Iterator[ClipboardItem]:
        """Stream a consistent export snapshot without a UI result limit."""
        with self._connection() as connection:
            for row in connection.execute(
                "SELECT * FROM clipboard_items ORDER BY pinned DESC, created_at DESC, id DESC"
            ):
                yield _item(row)

    def export_bibtex(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            for item in self.iter_items():
                if item.kind == "bibtex":
                    stream.write(item.content.strip() + "\n\n")

    def export_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            stream.write("[\n")
            for index, item in enumerate(self.iter_items()):
                if index:
                    stream.write(",\n")
                json.dump(asdict(item), stream, ensure_ascii=False, indent=2)
            stream.write("\n]\n")

    def export_markdown(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as stream:
            stream.write("# Academic Clipboard export\n\n")
            for item in self.iter_items():
                lines = [
                    f"## {item.title or item.kind}",
                    "",
                    f"- Type: `{item.kind}/{item.subtype}`",
                    f"- Captured: {item.created_at}",
                    f"- Pinned: {'yes' if item.pinned else 'no'}",
                    f"- Tags: {item.tags or '-'}",
                    f"- Project: {item.project or '-'}",
                    f"- Source: {item.source or '-'}",
                    f"- Locator: {item.locator or '-'}",
                ]
                if item.kind == "image":
                    lines += [f"- Image: `{item.media_path}`", f"- Dimensions: {item.width}×{item.height}"]
                lines += ["", item.normalized_content]
                if item.note:
                    lines += ["", f"> Note: {item.note}"]
                stream.write("\n".join(lines) + "\n\n")
