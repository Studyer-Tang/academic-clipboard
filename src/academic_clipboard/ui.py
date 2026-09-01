from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

KINDS = ("all", "image", "doi", "bibtex", "url", "code", "title", "text")
KIND_LABELS = {
    "all": "All / 全部",
    "image": "Image / 图片",
    "doi": "DOI",
    "bibtex": "BibTeX",
    "url": "URL",
    "code": "Code / 代码",
    "title": "Title / 标题",
    "text": "Text / 文本",
}
KIND_DISPLAY = {
    "image": "IMAGE",
    "doi": "DOI",
    "bibtex": "BIB",
    "url": "LINK",
    "code": "CODE",
    "title": "PAPER",
    "text": "TEXT",
}


def build_ui(app: Any) -> None:
    outer = ttk.Frame(app.root, padding=10)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(2, weight=1)

    heading = ttk.Frame(outer)
    heading.grid(row=0, column=0, sticky="ew", pady=(0, 9))
    app.title_label = ttk.Label(heading, text="Academic Clipboard", style="Title.TLabel")
    app.title_label.pack(side="left")
    app.settings_button = ttk.Button(heading, text="⚙", width=3, command=app.open_settings)
    app.settings_button.pack(side="right", padx=(5, 0))
    app.help_button = ttk.Button(heading, text="?", width=3, command=app.open_shortcuts)
    app.help_button.pack(side="right", padx=(5, 0))
    app.mode_button = ttk.Button(heading, text="Expand / 展开", command=app.toggle_window_mode)
    app.mode_button.pack(side="right", padx=(5, 0))
    app.capture_button = ttk.Button(heading, text="⏸", width=3, command=app.toggle_capture)
    app.capture_button.pack(side="right")

    toolbar = ttk.Frame(outer)
    toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    app.search_label = ttk.Label(toolbar, text="Search / 搜索")
    app.search_label.pack(side="left")
    app.search_var = tk.StringVar()
    app.search_entry = ttk.Entry(toolbar, textvariable=app.search_var, width=25)
    app.search_entry.pack(side="left", fill="x", expand=True, padx=(8, 10))
    app.search_var.trace_add("write", app._schedule_refresh)
    app.kind_var = tk.StringVar(value=KIND_LABELS["all"])
    kind = ttk.Combobox(
        toolbar,
        textvariable=app.kind_var,
        values=[KIND_LABELS[value] for value in KINDS],
        state="readonly",
        width=13,
    )
    kind.pack(side="left")
    kind.bind("<<ComboboxSelected>>", lambda _event: app.refresh())
    app.capture_now_button = ttk.Button(toolbar, text="Capture now / 立即保存", command=app.capture_now)
    app.capture_now_button.pack(side="left", padx=(10, 0))

    app.pane = ttk.Panedwindow(outer, orient="horizontal")
    app.pane.grid(row=2, column=0, sticky="nsew")
    app.list_frame = ttk.Frame(app.pane)
    app.detail_frame = ttk.Frame(app.pane, padding=(12, 0, 0, 0))
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
        ("pin", "★", 38, "center"),
        ("kind", "Type / 类型", 90, "center"),
        ("preview", "Content / 内容", 390, "w"),
        ("copies", "Copies", 60, "center"),
        ("time", "Captured / 时间", 150, "center"),
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
        text="Nothing captured yet\n复制截图、DOI、标题、代码或网址即可开始",
        style="Muted.TLabel",
        justify="center",
    )

    app.context_menu = tk.Menu(app.root, tearoff=False)
    app.context_menu.add_command(label="Copy / 复制", command=lambda: app.copy_selected(False))
    app.context_menu.add_command(label="Copy formatted / 复制格式化", command=lambda: app.copy_selected(True))
    app.context_menu.add_separator()
    app.context_menu.add_command(label="Edit & tags / 编辑与标签", command=app.edit_selected)
    app.context_menu.add_command(label="Pin / 置顶", command=app.toggle_pin)
    app.context_menu.add_command(label="Delete / 删除", command=app.delete_selected)
    app._style_context_menu()

    app.detail_title = ttk.Label(
        app.detail_frame,
        text="Select an item / 选择一项",
        font=("Segoe UI Semibold", 13),
    )
    app.detail_title.pack(fill="x")
    app.detail_meta = ttk.Label(
        app.detail_frame,
        text="",
        style="Muted.TLabel",
        wraplength=390,
    )
    app.detail_meta.pack(fill="x", pady=(4, 8))
    app.detail_body = ttk.Frame(app.detail_frame)
    app.detail_body.pack(fill="both", expand=True)
    app.detail_image = ttk.Label(app.detail_body, anchor="center")
    app.detail_text = tk.Text(
        app.detail_body,
        wrap="word",
        undo=False,
        font=("Cascadia Mono", 10),
        padx=10,
        pady=10,
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
    quick_actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
    for column in range(5):
        quick_actions.columnconfigure(column, weight=1)
    ttk.Button(
        quick_actions,
        text="复制",
        style="Accent.TButton",
        command=lambda: app.copy_selected(normalized=False),
    ).grid(row=0, column=0, sticky="ew")
    ttk.Button(
        quick_actions,
        text="格式",
        command=lambda: app.copy_selected(normalized=True),
    ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
    ttk.Button(quick_actions, text="编辑", command=app.edit_selected).grid(
        row=0, column=2, sticky="ew", padx=(4, 0)
    )
    ttk.Button(quick_actions, text="置顶", command=app.toggle_pin).grid(
        row=0, column=3, sticky="ew", padx=(4, 0)
    )
    ttk.Button(quick_actions, text="删除", command=app.delete_selected).grid(
        row=0, column=4, sticky="ew", padx=(4, 0)
    )

    bottom = ttk.Frame(outer)
    bottom.grid(row=4, column=0, sticky="ew", pady=(8, 0))
    app.status_var = tk.StringVar(
        value="Ready. Sensitive-looking text is skipped / 已就绪，疑似敏感内容默认不保存"
    )
    app.status_label = ttk.Label(bottom, textvariable=app.status_var, style="Muted.TLabel")
    app.status_label.pack(side="left", fill="x", expand=True)
    app.topmost_var = tk.BooleanVar(value=app.settings.always_on_top)
    app.topmost_check = ttk.Checkbutton(
        bottom,
        text="Always on top / 窗口置顶",
        variable=app.topmost_var,
        command=app._set_topmost,
    )
    app.topmost_check.pack(side="right", padx=(8, 0))
    app.export_button = ttk.Button(bottom, text="Export / 导出", command=app.export)
    app.export_button.pack(side="right", padx=(8, 0))
    app.clear_button = ttk.Button(
        bottom,
        text="Clear unpinned / 清空未置顶",
        command=app.clear_unpinned,
    )
    app.clear_button.pack(side="right")
