from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, ttk

from academic_clipboard.i18n import tr
from academic_clipboard.models import ClipboardItem
from academic_clipboard.settings import Settings
from academic_clipboard.theme import Palette

WINDOW_SHORTCUTS = (
    ("↑ / ↓", "Move through items / 上下选择条目"),
    ("Enter", "Copy selected item(s) / 复制所选内容"),
    ("1–9", "Quick-copy a recent item / 快速复制最近第 1–9 项"),
    ("E", "Edit the selected item / 编辑所选条目"),
    ("Ctrl+A", "Select all items / 选择全部条目"),
    ("Ctrl+F", "Focus search / 定位到搜索框"),
    ("Ctrl+Enter", "Copy original text / 复制原文"),
    ("Ctrl+Shift+Enter", "Copy formatted text / 复制格式化内容"),
    ("Delete", "Delete selected item(s) / 删除所选条目"),
    ("Esc", "Clear search, then hide window / 清空搜索，再按则隐藏窗口"),
    ("F1", "Open this shortcut guide / 打开快捷键说明"),
)


def _center(dialog: tk.Toplevel, parent: tk.Misc, width: int, height: int) -> None:
    parent.update_idletasks()
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")


def edit_item(
    parent: tk.Misc, item: ClipboardItem, palette: Palette
) -> tuple[str, str, str, str, str, str, str] | None:
    dialog = tk.Toplevel(parent)
    dialog.title(tr("整理研究片段", "Organize research clip"))
    dialog.transient(parent)
    dialog.configure(background=palette.background)
    dialog.minsize(560, 560)
    _center(dialog, parent, 680, 650)

    frame = ttk.Frame(dialog, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=tr("标题", "Title"), style="Section.TLabel").pack(anchor="w")
    title_var = tk.StringVar(value=item.title)
    title_entry = ttk.Entry(frame, textvariable=title_var)
    title_entry.pack(fill="x", pady=(4, 12))

    context = ttk.Frame(frame)
    context.pack(fill="x", pady=(0, 12))
    context.columnconfigure(0, weight=1)
    context.columnconfigure(1, weight=1)

    ttk.Label(context, text=tr("研究项目", "Project")).grid(row=0, column=0, sticky="w")
    ttk.Label(context, text=tr("标签（逗号分隔）", "Tags (comma separated)")).grid(
        row=0, column=1, sticky="w", padx=(10, 0)
    )
    project_var = tk.StringVar(value=item.project)
    ttk.Entry(context, textvariable=project_var).grid(row=1, column=0, sticky="ew", pady=(4, 9))
    tags_var = tk.StringVar(value=item.tags)
    ttk.Entry(context, textvariable=tags_var).grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(4, 9))

    ttk.Label(context, text=tr("来源（论文、网页或书名）", "Source (paper, page, or book)")).grid(
        row=2, column=0, sticky="w"
    )
    ttk.Label(context, text=tr("定位（页码、章节或图号）", "Locator (page, section, or figure)")).grid(
        row=2, column=1, sticky="w", padx=(10, 0)
    )
    source_var = tk.StringVar(value=item.source)
    locator_var = tk.StringVar(value=item.locator)
    ttk.Entry(context, textvariable=source_var).grid(row=3, column=0, sticky="ew", pady=(4, 0))
    ttk.Entry(context, textvariable=locator_var).grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(4, 0))

    ttk.Label(frame, text=tr("原文", "Content"), style="Section.TLabel").pack(anchor="w")
    content = tk.Text(
        frame,
        wrap="word",
        undo=True,
        font=("Cascadia Mono", 10),
        background=palette.surface,
        foreground=palette.text,
        insertbackground=palette.text,
        selectbackground=palette.selection,
        relief="solid",
        borderwidth=1,
        padx=9,
        pady=9,
    )
    content.insert("1.0", item.content)
    if item.kind == "image":
        content.configure(state="disabled")
    content.pack(fill="both", expand=True, pady=(4, 10))

    ttk.Label(frame, text=tr("研究批注", "Research note"), style="Section.TLabel").pack(anchor="w")
    note = tk.Text(
        frame,
        wrap="word",
        height=4,
        undo=True,
        font=("Segoe UI", 10),
        background=palette.surface,
        foreground=palette.text,
        insertbackground=palette.text,
        selectbackground=palette.selection,
        relief="solid",
        borderwidth=1,
        padx=9,
        pady=7,
    )
    note.insert("1.0", item.note)
    note.pack(fill="x", pady=(4, 12))

    result: list[tuple[str, str, str, str, str, str, str]] = []

    def save() -> None:
        value = item.content if item.kind == "image" else content.get("1.0", "end-1c")
        if not value.strip():
            messagebox.showerror(
                "Academic Clipboard", "Content cannot be empty / 内容不能为空", parent=dialog
            )
            return
        result.append(
            (
                title_var.get(),
                tags_var.get(),
                value,
                source_var.get(),
                locator_var.get(),
                project_var.get(),
                note.get("1.0", "end-1c"),
            )
        )
        dialog.destroy()

    actions = ttk.Frame(frame)
    actions.pack(fill="x")
    ttk.Button(actions, text=tr("取消", "Cancel"), command=dialog.destroy).pack(side="right")
    ttk.Button(actions, text=tr("保存", "Save"), style="Accent.TButton", command=save).pack(
        side="right", padx=(0, 8)
    )
    dialog.bind("<Command-Return>" if sys.platform == "darwin" else "<Control-Return>", lambda _event: save())
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    title_entry.focus_set()
    dialog.grab_set()
    parent.wait_window(dialog)
    return result[0] if result else None


def edit_settings(parent: tk.Misc, settings: Settings) -> bool:
    dialog = tk.Toplevel(parent)
    dialog.title("Settings / 设置")
    dialog.transient(parent)
    dialog.resizable(False, False)
    _center(dialog, parent, 550, 490)

    frame = ttk.Frame(dialog, padding=18)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    hotkey_var = tk.StringVar(value=settings.global_hotkey)
    theme_var = tk.StringVar(value=settings.theme)
    max_items_var = tk.StringVar(value=str(settings.max_items))
    retention_var = tk.StringVar(value=str(settings.retention_days))
    storage_var = tk.StringVar(value=str(settings.max_storage_mb))
    auto_hide_var = tk.BooleanVar(value=settings.auto_hide_after_copy)
    topmost_var = tk.BooleanVar(value=settings.always_on_top)
    sensitive_var = tk.BooleanVar(value=settings.capture_sensitive)

    rows = (
        ("Global hotkey / 全局快捷键", ttk.Entry(frame, textvariable=hotkey_var)),
        (
            "Theme / 主题",
            ttk.Combobox(
                frame,
                textvariable=theme_var,
                values=("system", "light", "dark"),
                state="readonly",
            ),
        ),
        ("Maximum items / 最大条目", ttk.Entry(frame, textvariable=max_items_var)),
        ("Retention days / 保留天数", ttk.Entry(frame, textvariable=retention_var)),
        ("Unpinned MiB / 未置顶容量", ttk.Entry(frame, textvariable=storage_var)),
    )
    for row, (label, widget) in enumerate(rows):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=7, padx=(0, 16))
        widget.grid(row=row, column=1, sticky="ew", pady=7)

    checks = ttk.Frame(frame)
    checks.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 4))
    ttk.Checkbutton(
        checks,
        text="Hide after copy / 复制后自动隐藏",
        variable=auto_hide_var,
    ).pack(anchor="w", pady=4)
    ttk.Checkbutton(
        checks,
        text="Always on top / 窗口置顶",
        variable=topmost_var,
    ).pack(anchor="w", pady=4)
    ttk.Checkbutton(
        checks,
        text="Allow sensitive-looking text / 允许保存疑似敏感内容",
        variable=sensitive_var,
    ).pack(anchor="w", pady=4)

    ttk.Label(
        frame,
        text="Examples: Ctrl+Alt+V, Ctrl+Shift+Space. Press F1 or click ? for the full guide.\n"
        "快捷键示例：Ctrl+Alt+V、Ctrl+Shift+Space。按 F1 或点击 ? 查看完整说明。",
        style="Muted.TLabel",
    ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 14))

    saved = tk.BooleanVar(value=False)

    def save() -> None:
        try:
            maximum = int(max_items_var.get())
            retention = int(retention_var.get())
            storage = int(storage_var.get())
            if not (10 <= maximum <= 10000 and 1 <= retention <= 3650 and 16 <= storage <= 4096):
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Academic Clipboard",
                "Items: 10–10000; days: 1–3650; MiB: 16–4096.\n容量限制不删除置顶内容；置顶项需手动管理。",
                parent=dialog,
            )
            return
        if not hotkey_var.get().strip():
            messagebox.showerror("Academic Clipboard", "Global hotkey cannot be empty.", parent=dialog)
            return
        settings.global_hotkey = hotkey_var.get().strip()
        settings.theme = theme_var.get()
        settings.max_items = maximum
        settings.retention_days = retention
        settings.max_storage_mb = storage
        settings.auto_hide_after_copy = auto_hide_var.get()
        settings.always_on_top = topmost_var.get()
        settings.capture_sensitive = sensitive_var.get()
        saved.set(True)
        dialog.destroy()

    actions = ttk.Frame(frame)
    actions.grid(row=7, column=0, columnspan=2, sticky="e")
    ttk.Button(actions, text="Cancel / 取消", command=dialog.destroy).pack(side="right")
    ttk.Button(actions, text="Save / 保存", style="Accent.TButton", command=save).pack(
        side="right", padx=(0, 8)
    )
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.grab_set()
    parent.wait_window(dialog)
    return saved.get()


def show_shortcuts(parent: tk.Misc, global_hotkey: str) -> None:
    dialog = tk.Toplevel(parent)
    dialog.title("Keyboard shortcuts / 快捷键说明")
    dialog.transient(parent)
    dialog.resizable(False, False)
    _center(dialog, parent, 570, 510)

    frame = ttk.Frame(dialog, padding=18)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    ttk.Label(frame, text="Keyboard shortcuts / 快捷键", style="Title.TLabel").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)
    )
    ttk.Label(
        frame,
        text="Use these while reading without leaving the keyboard. / 阅读时无需离开键盘。",
        style="Muted.TLabel",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

    ttk.Label(frame, text="Global / 全局", style="Section.TLabel").grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )
    ttk.Label(frame, text=global_hotkey, style="Key.TLabel").grid(
        row=3, column=0, sticky="w", padx=(0, 18), pady=4
    )
    ttk.Label(frame, text="Show and focus the clipboard / 唤出并聚焦剪贴板").grid(
        row=3, column=1, sticky="w", pady=4
    )

    ttk.Separator(frame).grid(row=4, column=0, columnspan=2, sticky="ew", pady=12)
    ttk.Label(frame, text="Inside the window / 窗口内", style="Section.TLabel").grid(
        row=5, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )
    for offset, (keys, description) in enumerate(WINDOW_SHORTCUTS, start=6):
        ttk.Label(
            frame, text=keys.replace("Ctrl", "Cmd") if sys.platform == "darwin" else keys, style="Key.TLabel"
        ).grid(row=offset, column=0, sticky="w", padx=(0, 18), pady=3)
        ttk.Label(frame, text=description).grid(row=offset, column=1, sticky="w", pady=3)

    actions = ttk.Frame(frame)
    actions.grid(row=6 + len(WINDOW_SHORTCUTS), column=0, columnspan=2, sticky="e", pady=(14, 0))
    ttk.Button(actions, text="Got it / 知道了", style="Accent.TButton", command=dialog.destroy).pack()
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.bind("<F1>", lambda _event: dialog.destroy())
    dialog.grab_set()
    dialog.focus_set()
    parent.wait_window(dialog)
