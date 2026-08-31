import subprocess
import sys
import unittest
import uuid
from pathlib import Path

from academic_clipboard.single_instance import SingleInstance
from academic_clipboard.startup import background_arguments
from academic_clipboard.tray import TrayController


class StartupTests(unittest.TestCase):
    def test_frozen_background_arguments_use_executable_directly(self) -> None:
        executable = Path("C:/Apps/AcademicClipboard.exe")
        self.assertEqual(
            background_arguments(executable, frozen=True),
            [str(executable), "run", "--hidden"],
        )

    def test_python_background_arguments_run_package(self) -> None:
        arguments = background_arguments(Path(sys.executable), frozen=False)
        self.assertEqual(arguments[-4:], ["-m", "academic_clipboard", "run", "--hidden"])
        self.assertIn("python", Path(arguments[0]).name.casefold())
        self.assertTrue(subprocess.list2cmdline(arguments))

    def test_tray_icon_is_generated_locally(self) -> None:
        image = TrayController._create_icon()
        self.assertEqual(image.size, (64, 64))
        self.assertEqual(image.mode, "RGBA")

    @unittest.skipUnless(sys.platform == "win32", "Windows mutex test")
    def test_windows_single_instance_mutex(self) -> None:
        name = f"Local\\AcademicClipboardTest-{uuid.uuid4()}"
        first = SingleInstance(name)
        second = SingleInstance(name)
        try:
            self.assertFalse(first.already_running)
            self.assertTrue(second.already_running)
        finally:
            second.close()
            first.close()


if __name__ == "__main__":
    unittest.main()
