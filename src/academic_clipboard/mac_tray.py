"""Cocoa menu bar item owned by Tk's main thread and native event loop."""

from __future__ import annotations

from AppKit import NSMenu, NSMenuItem, NSObject, NSStatusBar, NSVariableStatusItemLength


class MenuActions(NSObject):
    def show_(self, _sender):
        self.controller.on_show()

    def toggle_(self, _sender):
        self.controller.on_toggle_capture()

    def quit_(self, _sender):
        self.controller.on_quit()


class MacTray:
    def __init__(self, on_show, on_toggle_capture, on_quit, capture_enabled):
        self.on_show = on_show
        self.on_toggle_capture = on_toggle_capture
        self.on_quit = on_quit
        self.capture_enabled = capture_enabled
        self._actions = MenuActions.alloc().init()
        self._actions.controller = self
        self._item = None

    def start(self) -> None:
        self._item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self._item.button().setTitle_("AC")
        self._item.button().setToolTip_("Academic Clipboard")
        self.refresh()

    def refresh(self) -> None:
        menu = NSMenu.alloc().init()
        pause = "Pause / 暂停监听" if self.capture_enabled() else "Resume / 恢复监听"
        for title, action in (("Show / 显示", "show:"), (pause, "toggle:"), ("Quit / 退出", "quit:")):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
            item.setTarget_(self._actions)
            menu.addItem_(item)
        self._item.setMenu_(menu)

    def stop(self) -> None:
        if self._item is not None:
            NSStatusBar.systemStatusBar().removeStatusItem_(self._item)
            self._item = None
        self._actions.controller = None
