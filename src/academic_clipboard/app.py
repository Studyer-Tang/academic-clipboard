from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from queue import Empty, SimpleQueue
from tkinter import filedialog, messagebox

from academic_clipboard.dialogs import edit_item, edit_settings, show_shortcuts
from academic_clipboard.hotkeys import GlobalHotkey, parse_hotkey
from academic_clipboard.models import ClipboardItem
from academic_clipboard.privacy import sensitive_reason
from academic_clipboard.settings import Settings, application_dir
from academic_clipboard.storage import ClipboardStore
from academic_clipboard.theme import apply_theme
from academic_clipboard.ui import KIND_DISPLAY, KIND_LABELS, build_ui


class AcademicClipboardApp:
    def __init__(
        self,
        root: tk.Tk,
        store: ClipboardStore,
        settings: Settings,
        settings_path: Path,
        enable_tray: bool = True,
        enable_hotkey: bool | None = None,
    ):
        self.root = root
        self.store = store
        self.settings = settings
        self.settings_path = settings_path
        self.capture_enabled = True
        self.last_clipboard = ""
        self.items: dict[int, ClipboardItem] = {}
        self.search_after: str | None = None
        self.ui_actions: SimpleQueue[Callable[[], None]] = SimpleQueue()
        self.tray = None
        self.hotkey: GlobalHotkey | None = None
        self.shutting_down = False

        self.root.title("Academic Clipboard")
        self.root.attributes("-topmost", settings.always_on_top)
        self._configure_style()
        self._build_ui()
        self._bind_shortcuts()
        self._apply_window_mode()
        self.refresh()
        hotkey_enabled = enable_tray if enable_hotkey is None else enable_hotkey
        if hotkey_enabled:
            self._restart_hotkey()
        if enable_tray:
            self._start_tray()
        self.root.after(100, self._process_ui_actions)
        self.root.after(self.settings.poll_milliseconds, self._poll_clipboard)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_style(self) -> None:
        self.palette = apply_theme(self.root, self.settings.theme)

    def _build_ui(self) -> None:
        build_ui(self)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F1>", lambda _event: self.open_shortcuts())
        self.root.bind("<Control-f>", lambda _event: self._focus_search())
        self.root.bind("<Delete>", lambda _event: self.delete_selected())
        self.root.bind("<Control-Return>", lambda _event: self.copy_selected(normalized=False))
        self.root.bind("<Control-Shift-Return>", lambda _event: self.copy_selected(normalized=True))
        self.root.bind("<Escape>", lambda _event: self._handle_escape())
        self.tree.bind("<Control-a>", lambda _event: self.select_all())
        self.tree.bind("<Return>", lambda _event: self.copy_selected(normalized=False))
        self.tree.bind("<Key-e>", lambda _event: self.edit_selected())
        for number in range(1, 10):
            self.tree.bind(
                f"<Key-{number}>",
                lambda _event, index=number - 1: self._quick_copy_index(index),
            )

    def _style_context_menu(self) -> None:
        self.context_menu.configure(
            background=self.palette.surface,
            foreground=self.palette.text,
            activebackground=self.palette.selection,
            activeforeground=self.palette.text,
            borderwidth=1,
        )

    def _focus_search(self) -> str:
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")
        return "break"

    def _schedule_refresh(self, *_args: object) -> None:
        if self.search_after:
            self.root.after_cancel(self.search_after)
        self.search_after = self.root.after(180, self.refresh)

    def _selected_ids(self) -> list[int]:
        selected = set(self.tree.selection())
        return [int(item) for item in self.tree.get_children() if item in selected]

    def _selected_kind(self) -> str:
        label = self.kind_var.get()
        return next((key for key, value in KIND_LABELS.items() if value == label), "all")

    def select_all(self) -> str:
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children)
            self.tree.focus(children[0])
            self._show_detail()
        return "break"

    def _handle_escape(self) -> str:
        if self.search_var.get():
            self.search_var.set("")
        elif self.tray is not None:
            self.hide_window()
        return "break"

    def _quick_copy_index(self, index: int) -> str:
        children = self.tree.get_children()
        if index < len(children):
            self.tree.selection_set(children[index])
            self.tree.focus(children[index])
            self.copy_selected(normalized=False)
        return "break"

    def _show_context_menu(self, event: tk.Event) -> str:
        row = self.tree.identify_row(event.y)
        if row:
            if row not in self.tree.selection():
                self.tree.selection_set(row)
                self.tree.focus(row)
            self.context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _apply_window_mode(self) -> None:
        compact = self.settings.compact_mode
        detail_is_visible = str(self.detail_frame) in self.pane.panes()
        if compact:
            if detail_is_visible:
                self.pane.forget(self.detail_frame)
            self.tree.configure(displaycolumns=("pin", "kind", "preview"))
            self.tree.column("pin", width=34, stretch=False)
            self.tree.column("kind", width=72, stretch=False)
            self.capture_now_button.pack_forget()
            self.topmost_check.pack_forget()
            self.export_button.pack_forget()
            self.clear_button.pack_forget()
            self.status_label.configure(wraplength=380)
            self.mode_button.configure(text="Expand / 展开")
            width, height = 390, 380
            self.root.minsize(330, 260)
            x = max(0, self.root.winfo_screenwidth() - width - 24)
            y = 72
        else:
            if not detail_is_visible:
                self.pane.add(self.detail_frame, weight=2)
            self.tree.configure(displaycolumns=("pin", "kind", "preview", "copies", "time"))
            self.tree.column("pin", width=38, stretch=False)
            self.tree.column("kind", width=90, stretch=False)
            if not self.capture_now_button.winfo_manager():
                self.capture_now_button.pack(side="left", padx=(10, 0))
            if not self.topmost_check.winfo_manager():
                self.topmost_check.pack(side="right", padx=(8, 0))
                self.export_button.pack(side="right", padx=(8, 0))
                self.clear_button.pack(side="right")
            self.status_label.configure(wraplength=560)
            self.mode_button.configure(text="Compact / 悬浮")
            width, height = 1060, 680
            self.root.minsize(820, 520)
            x = max(0, (self.root.winfo_screenwidth() - width) // 2)
            y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def toggle_window_mode(self) -> None:
        self.settings.compact_mode = not self.settings.compact_mode
        self._apply_window_mode()

    def _restart_hotkey(self) -> None:
        if self.hotkey is not None:
            self.hotkey.stop()
        self.hotkey = GlobalHotkey(
            self.settings.global_hotkey,
            lambda: self._enqueue(self.show_window),
        )
        registered, error = self.hotkey.start()
        if not registered:
            self.status_var.set(f"Hotkey unavailable: {error} / 全局快捷键不可用")

    def _enqueue(self, action: Callable[[], None]) -> None:
        self.ui_actions.put(action)

    def _process_ui_actions(self) -> None:
        if self.shutting_down:
            return
        while True:
            try:
                action = self.ui_actions.get_nowait()
            except Empty:
                break
            action()
        self.root.after(100, self._process_ui_actions)

    def _start_tray(self) -> None:
        try:
            from academic_clipboard.tray import TrayController

            self.tray = TrayController(
                on_show=lambda: self._enqueue(self.show_window),
                on_toggle_capture=lambda: self._enqueue(self.toggle_capture),
                on_quit=lambda: self._enqueue(self.quit),
                capture_enabled=lambda: self.capture_enabled,
            )
            self.tray.start()
        except Exception as error:
            self.tray = None
            self.status_var.set(f"Tray unavailable: {error} / 系统托盘不可用")

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        children = self.tree.get_children()
        if children and not self.tree.selection():
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
        self.tree.focus_set()

    def hide_window(self) -> None:
        self.root.withdraw()

    def refresh(self) -> None:
        self.search_after = None
        selected = set(self.tree.selection())
        rows = self.store.list_items(self.search_var.get(), self._selected_kind())
        self.items = {item.id: item for item in rows}
        self.tree.delete(*self.tree.get_children())
        if rows:
            self.empty_label.place_forget()
        else:
            self.empty_label.place(relx=0.5, rely=0.48, anchor="center")
        for item in rows:
            preview = " ".join((item.title or item.content).split())
            if len(preview) > 90:
                preview = preview[:89] + "…"
            captured = item.created_at.replace("T", " ")[:19]
            self.tree.insert(
                "",
                "end",
                iid=str(item.id),
                values=(
                    "★" if item.pinned else "",
                    KIND_DISPLAY.get(item.kind, item.kind.upper()),
                    preview,
                    item.copy_count,
                    captured,
                ),
            )
        remaining = [identifier for identifier in selected if self.tree.exists(identifier)]
        if remaining:
            self.tree.selection_set(remaining)
        self.status_var.set(f"{len(rows)} items shown / 显示 {len(rows)} 项")
        self._show_detail()

    def _show_detail(self, _event: object | None = None) -> None:
        identifiers = self._selected_ids()
        if not identifiers:
            self.detail_title.configure(text="Select an item / 选择一项")
            self.detail_meta.configure(text="")
            body = ""
        elif len(identifiers) > 1:
            self.detail_title.configure(
                text=f"{len(identifiers)} items selected / 已选择 {len(identifiers)} 项"
            )
            self.detail_meta.configure(
                text="Copy them together in the visible list order / 将按当前列表顺序合并复制"
            )
            body = self.settings.join_separator.join(self.items[item].content for item in identifiers)
        else:
            item = self.items[identifiers[0]]
            self.detail_title.configure(text=item.title or item.kind)
            self.detail_meta.configure(
                text=f"{item.kind}/{item.subtype} · {item.created_at} · copied {item.copy_count} time(s)"
                + (f" · tags: {item.tags}" if item.tags else "")
            )
            body = item.content
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", body)
        self.detail_text.configure(state="disabled")

    def _read_clipboard(self) -> str:
        try:
            value = self.root.clipboard_get()
        except tk.TclError:
            return ""
        return value if isinstance(value, str) else ""

    def _capture(self, value: str, force: bool = False) -> bool:
        content = value.strip()
        if not content:
            return False
        if len(content) > self.settings.max_characters:
            self.status_var.set("Skipped: clipboard text is too large / 已跳过：文本过大")
            return False
        reason = sensitive_reason(content)
        if reason and not self.settings.capture_sensitive:
            self.status_var.set(f"Skipped possible {reason} / 已跳过疑似敏感内容")
            return False
        item = self.store.add(content)
        self.store.prune(self.settings.max_items, self.settings.retention_days)
        if force or not self.search_var.get():
            self.refresh()
        self.status_var.set(f"Captured {item.kind}/{item.subtype} / 已保存 {item.kind}/{item.subtype}")
        return True

    def _poll_clipboard(self) -> None:
        value = self._read_clipboard()
        if self.capture_enabled and value and value != self.last_clipboard:
            self.last_clipboard = value
            self._capture(value)
        elif value:
            self.last_clipboard = value
        self.root.after(self.settings.poll_milliseconds, self._poll_clipboard)

    def capture_now(self) -> None:
        value = self._read_clipboard()
        if not value.strip():
            self.status_var.set("No storable text in clipboard / 剪贴板中没有可保存文本")
            return
        self._capture(value, force=True)

    def _set_clipboard(self, value: str) -> None:
        self.last_clipboard = value
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update_idletasks()

    def copy_selected(self, normalized: bool) -> None:
        identifiers = self._selected_ids()
        items = self.store.get_many(identifiers)
        if not items:
            self.status_var.set("Select one or more items first / 请先选择一项或多项")
            return
        parts = [item.normalized_content if normalized else item.content for item in items]
        combined = self.settings.join_separator.join(parts)
        self._set_clipboard(combined)
        self.store.mark_copied(identifiers)
        self.refresh()
        mode = "formatted" if normalized else "original"
        self.status_var.set(f"Copied {len(items)} {mode} item(s) / 已复制 {len(items)} 项")
        if self.settings.auto_hide_after_copy and self.tray is not None:
            self.root.after(90, self.hide_window)

    def edit_selected(self) -> str:
        identifiers = self._selected_ids()
        if len(identifiers) != 1:
            self.status_var.set("Select exactly one item to edit / 请选择一项进行编辑")
            return "break"
        item = self.items.get(identifiers[0]) or self.store.get_many(identifiers)[0]
        result = edit_item(self.root, item, self.palette)
        if result is None:
            return "break"
        title, tags, content = result
        try:
            self.store.update(item.id, content, title, tags)
        except ValueError as error:
            messagebox.showerror("Academic Clipboard", str(error), parent=self.root)
            return "break"
        self.refresh()
        self.tree.selection_set(str(item.id))
        self.tree.focus(str(item.id))
        self._show_detail()
        self.status_var.set("Snippet updated / 片段已更新")
        return "break"

    def open_settings(self) -> None:
        previous_hotkey = self.settings.global_hotkey
        previous_theme = self.settings.theme
        if not edit_settings(self.root, self.settings):
            return
        try:
            parse_hotkey(self.settings.global_hotkey)
        except ValueError as error:
            self.settings.global_hotkey = previous_hotkey
            messagebox.showerror(
                "Academic Clipboard",
                f"Invalid hotkey: {error} / 快捷键格式无效",
                parent=self.root,
            )
        self.settings.save(self.settings_path)
        self.topmost_var.set(self.settings.always_on_top)
        self._set_topmost()
        if self.settings.theme != previous_theme:
            self.palette = apply_theme(self.root, self.settings.theme)
            self._style_context_menu()
            self.detail_text.configure(
                background=self.palette.surface,
                foreground=self.palette.text,
                insertbackground=self.palette.text,
                selectbackground=self.palette.selection,
            )
        if self.settings.global_hotkey != previous_hotkey:
            self._restart_hotkey()
        self.store.prune(self.settings.max_items, self.settings.retention_days)
        self.refresh()

    def open_shortcuts(self) -> str:
        show_shortcuts(self.root, self.settings.global_hotkey)
        return "break"

    def toggle_pin(self) -> None:
        identifiers = self._selected_ids()
        self.store.toggle_pinned(identifiers)
        self.refresh()

    def delete_selected(self) -> None:
        identifiers = self._selected_ids()
        if not identifiers:
            return
        if messagebox.askyesno(
            "Delete", f"Delete {len(identifiers)} selected item(s)?\n删除所选 {len(identifiers)} 项？"
        ):
            deleted = self.store.delete(identifiers)
            self.refresh()
            self.status_var.set(f"Deleted {deleted} item(s) / 已删除 {deleted} 项")

    def clear_unpinned(self) -> None:
        if messagebox.askyesno("Clear", "Delete all unpinned history?\n删除全部未置顶历史？"):
            deleted = self.store.clear_unpinned()
            self.refresh()
            self.status_var.set(
                f"Deleted {deleted} item(s); pinned items kept / 已删除 {deleted} 项，置顶项已保留"
            )

    def export(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export Academic Clipboard",
            defaultextension=".md",
            filetypes=(("Markdown", "*.md"), ("JSON", "*.json")),
        )
        if not path:
            return
        destination = Path(path)
        if destination.suffix.casefold() == ".json":
            self.store.export_json(destination)
        else:
            self.store.export_markdown(destination)
        self.status_var.set(f"Exported to {destination.name} / 已导出")

    def toggle_capture(self) -> None:
        self.capture_enabled = not self.capture_enabled
        self.capture_button.configure(text="⏸" if self.capture_enabled else "▶")
        self.status_var.set(
            "Capture active / 正在监听" if self.capture_enabled else "Capture paused / 已暂停监听"
        )
        if self.tray is not None:
            self.tray.refresh()

    def _set_topmost(self) -> None:
        self.settings.always_on_top = self.topmost_var.get()
        self.root.attributes("-topmost", self.settings.always_on_top)

    def close(self) -> None:
        if self.tray is not None:
            self.settings.save(self.settings_path)
            self.hide_window()
            return
        self.quit()

    def quit(self) -> None:
        if self.shutting_down:
            return
        self.shutting_down = True
        self.settings.save(self.settings_path)
        if self.tray is not None:
            self.tray.stop()
            self.tray = None
        if self.hotkey is not None:
            self.hotkey.stop()
            self.hotkey = None
        self.root.destroy()


def run(start_hidden: bool = False) -> int:
    from academic_clipboard.single_instance import SingleInstance, notify_already_running

    instance = SingleInstance()
    if instance.already_running:
        instance.close()
        notify_already_running()
        return 0
    home = application_dir()
    settings_path = home / "settings.json"
    settings = Settings.load(settings_path)
    store = ClipboardStore(home / "clipboard.db")
    try:
        root = tk.Tk()
        app = AcademicClipboardApp(root, store, settings, settings_path)
        if start_hidden:
            app.hide_window()
        root.mainloop()
    finally:
        instance.close()
    return 0
