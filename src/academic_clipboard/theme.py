from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True, slots=True)
class Palette:
    background: str
    surface: str
    elevated: str
    text: str
    muted: str
    border: str
    accent: str
    accent_text: str
    selection: str


LIGHT = Palette(
    background="#F3F6F5",
    surface="#FFFFFF",
    elevated="#E8EFEC",
    text="#17201D",
    muted="#64716C",
    border="#CDD8D3",
    accent="#176B5B",
    accent_text="#FFFFFF",
    selection="#CDE8DF",
)

DARK = Palette(
    background="#161B19",
    surface="#222926",
    elevated="#2A3430",
    text="#EEF4F1",
    muted="#A3B2AC",
    border="#3C4B45",
    accent="#45B89C",
    accent_text="#10201B",
    selection="#315E52",
)


def system_uses_dark() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _kind = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
    except (FileNotFoundError, OSError, ValueError):
        return False


def resolve_palette(theme: str) -> Palette:
    if theme == "dark" or (theme == "system" and system_uses_dark()):
        return DARK
    return LIGHT


def apply_theme(root: tk.Tk, theme: str) -> Palette:
    palette = resolve_palette(theme)
    root.configure(background=palette.background)
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure(
        ".",
        background=palette.background,
        foreground=palette.text,
        font=("Segoe UI", 10),
    )
    style.configure("TFrame", background=palette.background)
    style.configure("Surface.TFrame", background=palette.surface)
    style.configure("TLabel", background=palette.background, foreground=palette.text)
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 15), foreground=palette.text)
    style.configure("Section.TLabel", font=("Segoe UI Semibold", 10), foreground=palette.text)
    style.configure(
        "Key.TLabel",
        background=palette.elevated,
        foreground=palette.text,
        font=("Cascadia Mono", 9),
        padding=(6, 3),
    )
    style.configure("Muted.TLabel", foreground=palette.muted)
    style.configure(
        "TButton",
        background=palette.elevated,
        foreground=palette.text,
        bordercolor=palette.border,
        padding=(9, 6),
    )
    style.map("TButton", background=[("active", palette.selection)])
    style.configure(
        "Accent.TButton",
        background=palette.accent,
        foreground=palette.accent_text,
        bordercolor=palette.accent,
        font=("Segoe UI Semibold", 10),
    )
    style.map("Accent.TButton", background=[("active", palette.accent)])
    style.configure(
        "Treeview",
        background=palette.surface,
        fieldbackground=palette.surface,
        foreground=palette.text,
        bordercolor=palette.border,
        rowheight=32,
    )
    style.configure(
        "Treeview.Heading",
        background=palette.elevated,
        foreground=palette.text,
        bordercolor=palette.border,
        font=("Segoe UI Semibold", 9),
        padding=(6, 6),
    )
    style.map(
        "Treeview",
        background=[("selected", palette.selection)],
        foreground=[("selected", palette.text)],
    )
    style.configure(
        "TEntry",
        fieldbackground=palette.surface,
        foreground=palette.text,
        bordercolor=palette.border,
        insertcolor=palette.text,
        padding=(7, 6),
    )
    style.configure(
        "TCombobox",
        fieldbackground=palette.surface,
        foreground=palette.text,
        background=palette.elevated,
        bordercolor=palette.border,
        padding=(6, 5),
    )
    style.configure("TCheckbutton", background=palette.background, foreground=palette.text)
    return palette
