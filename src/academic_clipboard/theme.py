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
    background="#F6F7F9",
    surface="#FFFFFF",
    elevated="#EEF1F6",
    text="#182033",
    muted="#6D7688",
    border="#DCE1E9",
    accent="#315EEA",
    accent_text="#FFFFFF",
    selection="#E5EBFF",
)

DARK = Palette(
    background="#11151C",
    surface="#181E28",
    elevated="#222A38",
    text="#F1F4F9",
    muted="#98A2B5",
    border="#303A4B",
    accent="#7896FF",
    accent_text="#0E1526",
    selection="#293B70",
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
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 12), foreground=palette.text)
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
        relief="flat",
        padding=(10, 7),
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
        "Quiet.TButton",
        background=palette.background,
        foreground=palette.muted,
        bordercolor=palette.background,
        padding=(7, 6),
    )
    style.map("Quiet.TButton", background=[("active", palette.elevated)])
    style.configure(
        "Treeview",
        background=palette.surface,
        fieldbackground=palette.surface,
        foreground=palette.text,
        bordercolor=palette.border,
        rowheight=38,
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
