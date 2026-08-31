from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from queue import Empty, SimpleQueue
from tkinter import filedialog, messagebox, ttk

from academic_clipboard.models import ClipboardItem
from academic_clipboard.privacy import sensitive_reason
from academic_clipboard.settings import Settings, application_dir
from academic_clipboard.storage import ClipboardStore

KINDS = ("all", "doi", "bibtex", "url", "code", "title", "text")
KIND_LABELS = {
    "all": "All / 全部",
    "doi": "DOI",
    "bibtex": "BibTeX",
    "url": "URL",
    "code": "Code / 代码",
    "title": "Title / 标题",
    "text": "Text / 文本",
}


class AcademicClipboardApp:
    def __init__(
        self,
        root: tk.Tk,
        store: ClipboardStore,
        settings: Settings,
        settings_path: Path,
        enable_tray: bool = True,
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
        self.shutting_down = False

        self.root.title("Academic Clipboard")
        self.root.attributes("-topmost", settings.always_on_top)
        self._configure_style()
        self._build_ui()
        self._bind_shortcuts()
        self._apply_window_mode()
        self.refresh()
        if enable_tray:
            self._start_tray()
        self.root.after(100, self._process_ui_actions)
        self.root.after(self.settings.poll_milliseconds, self._poll_clipboard)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=30)
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", foreground="#5f6b66")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        heading = ttk.Frame(outer)
        heading.pack(fill="x", pady=(0, 12))
        self.title_label = ttk.Label(heading, text="Academic Clipboard", style="Title.TLabel")
        self.title_label.pack(side="left")
        self.mode_button = ttk.Button(heading, text="Expand / 展开", command=self.toggle_window_mode)
        self.mode_button.pack(side="right")
        self.capture_button = ttk.Button(heading, text="Pause / 暂停", command=self.toggle_capture)
        self.capture_button.pack(side="right")

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        self.search_label = ttk.Label(toolbar, text="Search / 搜索")
        self.search_label.pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=25)
        search.pack(side="left", fill="x", expand=True, padx=(8, 10))
        self.search_entry = search
        self.search_var.trace_add("write", self._schedule_refresh)
        self.kind_var = tk.StringVar(value=KIND_LABELS["all"])
        kind = ttk.Combobox(
            toolbar,
            textvariable=self.kind_var,
            values=[KIND_LABELS[value] for value in KINDS],
            state="readonly",
            width=13,
        )
        kind.pack(side="left")
        kind.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.capture_now_button = ttk.Button(toolbar, text="Capture now / 立即保存", command=self.capture_now)
        self.capture_now_button.pack(side="left", padx=(10, 0))

        self.pane = ttk.Panedwindow(outer, orient="horizontal")
        self.pane.pack(fill="both", expand=True)
        self.list_frame = ttk.Frame(self.pane)
        self.detail_frame = ttk.Frame(self.pane, padding=(12, 0, 0, 0))
        self.pane.add(self.list_frame, weight=3)
        self.pane.add(self.detail_frame, weight=2)

        columns = ("pin", "kind", "preview", "copies", "time")
        self.tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", selectmode="extended")
        for key, text, width, anchor in (
            ("pin", "★", 38, "center"),
            ("kind", "Type / 类型", 90, "center"),
            ("preview", "Content / 内容", 390, "w"),
            ("copies", "Copies", 60, "center"),
            ("time", "Captured / 时间", 150, "center"),
        ):
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, anchor=anchor, stretch=key == "preview")
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._show_detail)
        self.tree.bind("<Double-1>", lambda _event: self.copy_selected(normalized=False))

        self.detail_title = ttk.Label(
            self.detail_frame, text="Select an item / 选择一项", font=("Segoe UI", 13, "bold")
        )
        self.detail_title.pack(fill="x")
        self.detail_meta = ttk.Label(self.detail_frame, text="", style="Muted.TLabel", wraplength=390)
        self.detail_meta.pack(fill="x", pady=(4, 8))
        text_wrap = ttk.Frame(self.detail_frame)
        text_wrap.pack(fill="both", expand=True)
        self.detail_text = tk.Text(
            text_wrap,
            wrap="word",
            undo=False,
            font=("Cascadia Mono", 10),
            padx=10,
            pady=10,
            relief="solid",
            borderwidth=1,
        )
        detail_scroll = ttk.Scrollbar(text_wrap, orient="vertical", command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scroll.set)
        self.detail_text.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")
        self.detail_text.configure(state="disabled")

        quick_actions = ttk.Frame(outer)
        quick_actions.pack(fill="x", pady=(8, 0))
        for column in range(5):
            quick_actions.columnconfigure(column, weight=1)
        ttk.Button(
            quick_actions,
            text="Copy / 复制",
            style="Accent.TButton",
            command=lambda: self.copy_selected(normalized=False),
        ).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            quick_actions,
            text="Format / 格式化",
            command=lambda: self.copy_selected(normalized=True),
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ttk.Button(quick_actions, text="All / 全选", command=self.select_all).grid(
            row=0, column=2, sticky="ew", padx=(4, 0)
        )
        ttk.Button(quick_actions, text="Pin / 置顶", command=self.toggle_pin).grid(
            row=0, column=3, sticky="ew", padx=(4, 0)
        )
        ttk.Button(quick_actions, text="Delete / 删除", command=self.delete_selected).grid(
            row=0, column=4, sticky="ew", padx=(4, 0)
        )

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(10, 0))
        self.status_var = tk.StringVar(
            value="Ready. Sensitive-looking text is skipped / 已就绪，疑似敏感内容默认不保存"
        )
        self.status_label = ttk.Label(bottom, textvariable=self.status_var, style="Muted.TLabel")
        self.status_label.pack(side="left", fill="x", expand=True)
        self.topmost_var = tk.BooleanVar(value=self.settings.always_on_top)
        self.topmost_check = ttk.Checkbutton(
            bottom,
            text="Always on top / 窗口置顶",
            variable=self.topmost_var,
            command=self._set_topmost,
        )
        self.topmost_check.pack(side="right", padx=(8, 0))
        self.export_button = ttk.Button(bottom, text="Export / 导出", command=self.export)
        self.export_button.pack(side="right", padx=(8, 0))
        self.clear_button = ttk.Button(
            bottom, text="Clear unpinned / 清空未置顶", command=self.clear_unpinned
        )
        self.clear_button.pack(side="right")

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-f>", lambda _event: self._focus_search())
        self.root.bind("<Delete>", lambda _event: self.delete_selected())
        self.root.bind("<Control-Return>", lambda _event: self.copy_selected(normalized=False))
        self.root.bind("<Control-Shift-Return>", lambda _event: self.copy_selected(normalized=True))
        self.root.bind("<Escape>", lambda _event: self.search_var.set(""))
        self.tree.bind("<Control-a>", lambda _event: self.select_all())

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
        self.root.after_idle(self.root.focus_force)

    def hide_window(self) -> None:
        self.root.withdraw()

    def refresh(self) -> None:
        self.search_after = None
        selected = set(self.tree.selection())
        rows = self.store.list_items(self.search_var.get(), self._selected_kind())
        self.items = {item.id: item for item in rows}
        self.tree.delete(*self.tree.get_children())
        for item in rows:
            preview = " ".join(item.content.split())
            if len(preview) > 90:
                preview = preview[:89] + "…"
            captured = item.created_at.replace("T", " ")[:19]
            self.tree.insert(
                "",
                "end",
                iid=str(item.id),
                values=("★" if item.pinned else "", item.kind, preview, item.copy_count, captured),
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
        self.capture_button.configure(text="Pause / 暂停" if self.capture_enabled else "Resume / 恢复")
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
