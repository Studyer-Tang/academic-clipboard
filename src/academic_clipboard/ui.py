from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from academic_clipboard.i18n import tr

KINDS = ("all", "image", "doi", "bibtex", "url", "formula", "table", "code", "title", "text")
KIND_LABELS = {
    "all": tr("全部", "All"),
    "image": tr("图片", "Images"),
    "doi": "DOI",
    "bibtex": "BibTeX",
    "url": tr("链接", "Links"),
    "formula": tr("公式", "Formulae"),
    "table": tr("表格", "Tables"),
    "code": tr("代码", "Code"),
    "title": tr("论文标题", "Paper titles"),
    "text": tr("文本", "Text"),
}
KIND_DISPLAY = {
    "image": "IMAGE",
    "doi": "DOI",
    "bibtex": "BIB",
    "url": "LINK",
    "formula": "MATH",
    "table": "TABLE",
    "code": "CODE",
    "title": "PAPER",
    "text": "TEXT",
}


def build_ui(app: Any) -> None:
    outer = ttk.Frame(app.root, padding=12)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(2, weight=1)

    heading = ttk.Frame(outer)
    heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    app.brand_mark = tk.Label(
        heading,
        text="●",
        font=("Segoe UI", 10),
        background=app.palette.background,
        foreground=app.palette.accent,
    )
    app.brand_mark.pack(side="left", padx=(0, 7))
    app.title_label = ttk.Label(heading, text="Academic Clipboard", style="Title.TLabel")
    app.title_label.pack(side="left")
    app.capture_status = ttk.Label(heading, text=tr("监听中", "Listening"), style="Muted.TLabel")
    app.capture_status.pack(side="left", padx=(10, 0))
    app.settings_button = ttk.Button(
        heading, text="⚙", width=3, style="Quiet.TButton", command=app.open_settings
    )
    app.settings_button.pack(side="right")
    app.help_button = ttk.Button(
        heading, text="?", width=3, style="Quiet.TButton", command=app.open_shortcuts
    )
    app.help_button.pack(side="right", padx=(2, 0))
    app.mode_button = ttk.Button(
        heading, text="↗", width=3, style="Quiet.TButton", command=app.toggle_window_mode
    )
    app.mode_button.pack(side="right", padx=(2, 0))
    app.capture_button = ttk.Button(
        heading, text="Ⅱ", width=3, style="Quiet.TButton", command=app.toggle_capture
    )
    app.capture_button.pack(side="right", padx=(2, 0))

    toolbar = ttk.Frame(outer)
    toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 9))
    app.search_label = ttk.Label(toolbar, text="⌕", font=("Segoe UI", 13))
    app.search_label.pack(side="left", padx=(0, 6))
    app.search_var = tk.StringVar()
    app.search_entry = ttk.Entry(toolbar, textvariable=app.search_var)
    app.search_entry.pack(side="left", fill="x", expand=True)
    app.search_var.trace_add("write", app._schedule_refresh)
    app.kind_var = tk.StringVar(value=KIND_LABELS["all"])
    app.kind_box = ttk.Combobox(
        toolbar,
        textvariable=app.kind_var,
        values=[KIND_LABELS[value] for value in KINDS],
        state="readonly",
        width=10,
    )
    app.kind_box.pack(side="left", padx=(8, 0))
    app.kind_box.bind("<<ComboboxSelected>>", lambda _event: app.refresh())
    app.capture_now_button = ttk.Button(toolbar, text=tr("立即保存", "Capture"), command=app.capture_now)
    app.capture_now_button.pack(side="left", padx=(8, 0))

    app.pane = ttk.Panedwindow(outer, orient="horizontal")
    app.pane.grid(row=2, column=0, sticky="nsew")
    app.list_frame = ttk.Frame(app.pane)
    app.detail_frame = ttk.Frame(app.pane, padding=(14, 0, 0, 0))
    app.pane.add(app.list_frame, weight=3)
    app.pane.add(app.detail_frame, weight=2)

    columns = ("pin", "kind", "preview", "copies", "time")
    app.tree = ttk.Treeview(
        app.list_frame,
        columns=columns,
        show="headings",
        selectmode="extended",
    )
    for key, text, width, anchor in (
        ("pin", "★", 34, "center"),
        ("kind", tr("类型", "Type"), 78, "center"),
        ("preview", tr("内容", "Content"), 390, "w"),
        ("copies", tr("次数", "Uses"), 58, "center"),
        ("time", tr("保存时间", "Captured"), 142, "center"),
    ):
        app.tree.heading(key, text=text)
        app.tree.column(key, width=width, anchor=anchor, stretch=key == "preview")
    scrollbar = ttk.Scrollbar(app.list_frame, orient="vertical", command=app.tree.yview)
    app.tree.configure(yscrollcommand=scrollbar.set)
    app.tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    app.tree.bind("<<TreeviewSelect>>", app._show_detail)
    app.tree.bind("<Double-1>", lambda _event: app.copy_selected(normalized=False))
    app.tree.bind("<Button-3>", app._show_context_menu)
    app.empty_label = ttk.Label(
        app.list_frame,
        text=tr(
            "复制论文标题、DOI、表格或公式即可开始", "Copy a paper title, DOI, table, or formula to begin"
        ),
        style="Muted.TLabel",
        justify="center",
        wraplength=280,
    )

    app.compact_preview_card = tk.Frame(
        app.list_frame,
        background=app.palette.surface,
        highlightbackground=app.palette.border,
        highlightthickness=1,
        padx=5,
        pady=5,
    )
    app.compact_preview_image = tk.Label(
        app.compact_preview_card,
        background=app.palette.surface,
        borderwidth=0,
        cursor="hand2",
    )
    app.compact_preview_image.pack()
    app.compact_preview_caption = tk.Label(
        app.compact_preview_card,
        background=app.palette.surface,
        foreground=app.palette.muted,
        font=("Segoe UI", 8),
        cursor="hand2",
    )
    app.compact_preview_caption.pack(fill="x", pady=(3, 0))
    for widget in (app.compact_preview_card, app.compact_preview_image, app.compact_preview_caption):
        widget.bind("<Double-1>", lambda _event: app.copy_selected(normalized=False))

    app.context_menu = tk.Menu(app.root, tearoff=False)
    app.context_menu.add_command(
        label=tr("复制原文", "Copy original"), command=lambda: app.copy_selected(False)
    )
    app.context_menu.add_command(label=tr("转换并复制…", "Copy as…"), command=app.show_transform_menu)
    app.context_menu.add_separator()
    app.context_menu.add_command(
        label=tr("整理研究信息", "Organize research context"), command=app.edit_selected
    )
    app.context_menu.add_command(label=tr("置顶", "Pin"), command=app.toggle_pin)
    app.context_menu.add_command(label=tr("删除", "Delete"), command=app.delete_selected)
    app.transform_menu = tk.Menu(app.root, tearoff=False)
    app._style_context_menu()

    app.detail_title = ttk.Label(
        app.detail_frame,
        text=tr("选择一条记录", "Select an item"),
        font=("Segoe UI Semibold", 13),
    )
    app.detail_title.pack(fill="x")
    app.detail_meta = ttk.Label(app.detail_frame, text="", style="Muted.TLabel", wraplength=390)
    app.detail_meta.pack(fill="x", pady=(5, 9))
    app.detail_body = ttk.Frame(app.detail_frame)
    app.detail_body.pack(fill="both", expand=True)
    app.detail_image = ttk.Label(app.detail_body, anchor="center")
    app.detail_text = tk.Text(
        app.detail_body,
        wrap="word",
        undo=False,
        font=("Cascadia Mono", 10),
        padx=11,
        pady=11,
        relief="solid",
        borderwidth=1,
        background=app.palette.surface,
        foreground=app.palette.text,
        insertbackground=app.palette.text,
        selectbackground=app.palette.selection,
    )
    app.detail_scroll = ttk.Scrollbar(app.detail_body, orient="vertical", command=app.detail_text.yview)
    app.detail_text.configure(yscrollcommand=app.detail_scroll.set)
    app.detail_text.pack(side="left", fill="both", expand=True)
    app.detail_scroll.pack(side="right", fill="y")
    app.detail_text.configure(state="disabled")

    quick_actions = ttk.Frame(outer)
    quick_actions.grid(row=3, column=0, sticky="ew", pady=(9, 0))
    for column in range(6):
        quick_actions.columnconfigure(column, weight=1)
    app.copy_button = ttk.Button(
        quick_actions,
        text=tr("复制", "Copy"),
        style="Accent.TButton",
        command=lambda: app.copy_selected(normalized=False),
    )
    app.copy_button.grid(row=0, column=0, sticky="ew")
    app.transform_button = ttk.Button(
        quick_actions, text=tr("转换", "Copy as"), command=app.show_transform_menu
    )
    app.transform_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))
    app.edit_button = ttk.Button(quick_actions, text=tr("整理", "Organize"), command=app.edit_selected)
    app.edit_button.grid(row=0, column=2, sticky="ew", padx=(5, 0))
    app.pin_button = ttk.Button(quick_actions, text=tr("置顶", "Pin"), command=app.toggle_pin)
    app.pin_button.grid(row=0, column=3, sticky="ew", padx=(5, 0))
    app.delete_button = ttk.Button(quick_actions, text=tr("删除", "Delete"), command=app.delete_selected)
    app.delete_button.grid(row=0, column=4, sticky="ew", padx=(5, 0))
    app.more_button = ttk.Button(quick_actions, text="···", command=app.show_more_menu)
    app.more_button.grid(row=0, column=5, sticky="ew", padx=(5, 0))

    bottom = ttk.Frame(outer)
    bottom.grid(row=4, column=0, sticky="ew", pady=(8, 0))
    app.status_var = tk.StringVar(value=tr("仅保存在本机", "Stored only on this device"))
    app.status_label = ttk.Label(bottom, textvariable=app.status_var, style="Muted.TLabel")
    app.status_label.pack(side="left", fill="x", expand=True)
    app.topmost_var = tk.BooleanVar(value=app.settings.always_on_top)
    app.topmost_check = ttk.Checkbutton(
        bottom,
        text=tr("置顶", "Always on top"),
        variable=app.topmost_var,
        command=app._set_topmost,
    )
    app.topmost_check.pack(side="right", padx=(8, 0))
    app.export_button = ttk.Button(bottom, text=tr("导出", "Export"), command=app.export)
    app.export_button.pack(side="right", padx=(8, 0))
    app.clear_button = ttk.Button(bottom, text=tr("清理历史", "Clear history"), command=app.clear_unpinned)
    app.clear_button.pack(side="right")
