from __future__ import annotations

import argparse
import json
from pathlib import Path

from academic_clipboard.models import ClipboardItem
from academic_clipboard.settings import application_dir
from academic_clipboard.storage import ClipboardStore


def _store(database: Path | None) -> ClipboardStore:
    return ClipboardStore(database or application_dir() / "clipboard.db")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="academic-clipboard",
        description="Local-first clipboard and research-snippet manager.",
    )
    parser.add_argument("--database", type=Path, help="override the local SQLite database path")
    commands = parser.add_subparsers(dest="command")
    run_command = commands.add_parser("run", help="open the desktop clipboard drawer")
    run_command.add_argument("--hidden", action="store_true", help="start in the system tray")
    commands.add_parser("launch", help="start the Windows tray app without keeping a terminal open")

    startup = commands.add_parser("startup", help="manage launch at Windows sign-in")
    startup.add_argument("action", choices=("enable", "disable", "status"), nargs="?", default="status")

    listing = commands.add_parser("list", help="list recent clipboard items")
    listing.add_argument("--kind", default="all")
    listing.add_argument("--limit", type=int, default=30)
    listing.add_argument("--json", action="store_true")

    search = commands.add_parser("search", help="search clipboard text and metadata")
    search.add_argument("query")
    search.add_argument("--kind", default="all")
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--json", action="store_true")

    export = commands.add_parser("export", help="export local history")
    export.add_argument("path", type=Path)
    export.add_argument("--format", choices=("markdown", "json"))

    clear = commands.add_parser("clear", help="delete clipboard history")
    clear.add_argument("--all", action="store_true", help="also delete pinned items")
    clear.add_argument("--yes", action="store_true", help="confirm deletion")
    commands.add_parser("stats", help="show local storage statistics")
    return parser


def _rows_payload(rows: list[ClipboardItem]) -> list[dict[str, object]]:
    return [
        {
            "id": item.id,
            "kind": item.kind,
            "subtype": item.subtype,
            "title": item.title,
            "created_at": item.created_at,
            "pinned": item.pinned,
            "tags": item.tags,
            "content": item.content,
            "media_path": item.media_path,
            "width": item.width,
            "height": item.height,
        }
        for item in rows
    ]


def _print_rows(rows: list[ClipboardItem], as_json: bool) -> None:
    payload = _rows_payload(rows)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not payload:
        print("No clipboard items.")
        return
    for item in payload:
        preview = " ".join(str(item["content"]).split())
        if len(preview) > 80:
            preview = preview[:79] + "…"
        pin = "★" if item["pinned"] else " "
        print(f"{pin} {item['id']:>5}  {item['kind']:<7} {item['subtype']:<12} {preview}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {None, "run"}:
        try:
            from academic_clipboard.app import run
        except ModuleNotFoundError as error:
            if error.name != "tkinter":
                raise
            parser.exit(
                1,
                "error: this Python installation does not include Tkinter. "
                "Install a standard Python build with Tcl/Tk. / 当前 Python 不含 Tkinter，"
                "请安装带 Tcl/Tk 的标准版 Python。\n",
            )

        return run(start_hidden=getattr(args, "hidden", False))
    if args.command == "launch":
        from academic_clipboard.startup import launch_background

        try:
            launch_background()
        except OSError as error:
            parser.error(str(error))
        print("Academic Clipboard started in the background / 已在后台启动")
        return 0
    if args.command == "startup":
        from academic_clipboard.startup import set_startup, startup_command

        try:
            if args.action == "enable":
                set_startup(True)
                print("startup=enabled / 已启用开机启动")
            elif args.action == "disable":
                set_startup(False)
                print("startup=disabled / 已关闭开机启动")
            else:
                command = startup_command()
                print("startup=enabled" if command else "startup=disabled")
                if command:
                    print(f"command={command}")
        except OSError as error:
            parser.error(str(error))
        return 0
    store = _store(args.database)
    if args.command == "list":
        _print_rows(store.list_items(kind=args.kind, limit=args.limit), args.json)
    elif args.command == "search":
        _print_rows(store.list_items(args.query, args.kind, args.limit), args.json)
    elif args.command == "export":
        output_format = args.format or ("json" if args.path.suffix.casefold() == ".json" else "markdown")
        if output_format == "json":
            store.export_json(args.path)
        else:
            store.export_markdown(args.path)
        print(f"exported={args.path}")
    elif args.command == "clear":
        if not args.yes:
            parser.error("clear requires --yes")
        deleted = store.clear_all() if args.all else store.clear_unpinned()
        print(f"deleted={deleted}")
    elif args.command == "stats":
        print(f"database={store.path}")
        print(f"items={store.count()}")
    return 0
