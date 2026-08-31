from __future__ import annotations

from collections.abc import Callable


class TrayController:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_toggle_capture: Callable[[], None],
        on_quit: Callable[[], None],
        capture_enabled: Callable[[], bool],
    ):
        import pystray

        self._pystray = pystray
        self._on_show = on_show
        self._on_toggle_capture = on_toggle_capture
        self._on_quit = on_quit
        self._capture_enabled = capture_enabled
        menu = pystray.Menu(
            pystray.MenuItem("Show / 显示", self._show, default=True),
            pystray.MenuItem(self._capture_label, self._toggle_capture),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit / 退出", self._quit),
        )
        self.icon = pystray.Icon(
            "academic-clipboard",
            self._create_icon(),
            "Academic Clipboard",
            menu,
        )

    @staticmethod
    def _create_icon():
        from PIL import Image, ImageDraw

        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 59, 59), radius=13, fill="#176B5B")
        draw.rounded_rectangle((16, 14, 48, 51), radius=4, fill="#F7FAF8")
        draw.rounded_rectangle((23, 9, 41, 19), radius=4, fill="#F2B84B")
        draw.line((22, 29, 42, 29), fill="#176B5B", width=4)
        draw.line((22, 37, 39, 37), fill="#176B5B", width=4)
        draw.line((22, 45, 35, 45), fill="#176B5B", width=4)
        return image

    def _capture_label(self, _item: object) -> str:
        return "Pause capture / 暂停监听" if self._capture_enabled() else "Resume capture / 恢复监听"

    def _show(self, _icon: object, _item: object) -> None:
        self._on_show()

    def _toggle_capture(self, _icon: object, _item: object) -> None:
        self._on_toggle_capture()

    def _quit(self, _icon: object, _item: object) -> None:
        self._on_quit()

    def start(self) -> None:
        self.icon.run_detached()

    def refresh(self) -> None:
        self.icon.update_menu()

    def stop(self) -> None:
        self.icon.stop()
