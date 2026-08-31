from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

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


def edit_item(parent: tk.Misc, item: ClipboardItem, palette: Palette) -> tuple[str, str, str] | None:
    dialog = tk.Toplevel(parent)
    dialog.title("Edit snippet / 编辑片段")
    dialog.transient(parent)
    dialog.configure(background=palette.background)
    dialog.minsize(480, 390)
    _center(dialog, parent, 620, 480)

    frame = ttk.Frame(dialog, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Title / 标题").pack(anchor="w")
    title_var = tk.StringVar(value=item.title)
    title_entry = ttk.Entry(frame, textvariable=title_var)
    title_entry.pack(fill="x", pady=(4, 12))

    ttk.Label(frame, text="Tags / 标签（用逗号分隔）").pack(anchor="w")
    tags_var = tk.StringVar(value=item.tags)
    ttk.Entry(frame, textvariable=tags_var).pack(fill="x", pady=(4, 12))

    ttk.Label(frame, text="Content / 内容").pack(anchor="w")
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
    content.pack(fill="both", expand=True, pady=(4, 12))

    result: list[tuple[str, str, str]] = []

    def save() -> None:
        value = content.get("1.0", "end-1c").strip()
        if not value:
            messagebox.showerror(
                "Academic Clipboard", "Content cannot be empty / 内容不能为空", parent=dialog
            )
            return
        result.append((title_var.get(), tags_var.get(), value))
        dialog.destroy()

    actions = ttk.Frame(frame)
    actions.pack(fill="x")
    ttk.Button(actions, text="Cancel / 取消", command=dialog.destroy).pack(side="right")
    ttk.Button(actions, text="Save / 保存", style="Accent.TButton", command=save).pack(
        side="right", padx=(0, 8)
    )
    dialog.bind("<Control-Return>", lambda _event: save())
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
    _center(dialog, parent, 520, 430)

    frame = ttk.Frame(dialog, padding=18)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    hotkey_var = tk.StringVar(value=settings.global_hotkey)
    theme_var = tk.StringVar(value=settings.theme)
    max_items_var = tk.StringVar(value=str(settings.max_items))
    retention_var = tk.StringVar(value=str(settings.retention_days))
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
    )
    for row, (label, widget) in enumerate(rows):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=7, padx=(0, 16))
        widget.grid(row=row, column=1, sticky="ew", pady=7)

    checks = ttk.Frame(frame)
    checks.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 4))
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
    ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 14))

    saved = tk.BooleanVar(value=False)

    def save() -> None:
        try:
            maximum = int(max_items_var.get())
            retention = int(retention_var.get())
            if maximum < 10 or retention < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Academic Clipboard",
                "Maximum items must be at least 10 and retention at least 1 day.\n"
                "最大条目不能少于 10，保留天数不能少于 1。",
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
        settings.auto_hide_after_copy = auto_hide_var.get()
        settings.always_on_top = topmost_var.get()
        settings.capture_sensitive = sensitive_var.get()
        saved.set(True)
        dialog.destroy()

    actions = ttk.Frame(frame)
    actions.grid(row=6, column=0, columnspan=2, sticky="e")
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
        ttk.Label(frame, text=keys, style="Key.TLabel").grid(
            row=offset, column=0, sticky="w", padx=(0, 18), pady=3
        )
        ttk.Label(frame, text=description).grid(row=offset, column=1, sticky="w", pady=3)

    actions = ttk.Frame(frame)
    actions.grid(row=6 + len(WINDOW_SHORTCUTS), column=0, columnspan=2, sticky="e", pady=(14, 0))
    ttk.Button(actions, text="Got it / 知道了", style="Accent.TButton", command=dialog.destroy).pack()
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.bind("<F1>", lambda _event: dialog.destroy())
    dialog.grab_set()
    dialog.focus_set()
    parent.wait_window(dialog)
