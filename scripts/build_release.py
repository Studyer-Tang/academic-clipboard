"""Build a native, self-contained directory bundle; no extraction on every launch."""

import hashlib
import importlib.metadata
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from academic_clipboard import __version__
from academic_clipboard.tray import TrayController


def main():
    if sys.platform not in {"win32", "darwin"}:
        raise SystemExit("Build on Windows or macOS for that operating system.")
    assets = Path("build-assets")
    assets.mkdir(exist_ok=True)
    mac = sys.platform == "darwin"
    icon = assets / ("academic-clipboard.icns" if mac else "academic-clipboard.ico")
    TrayController._create_icon().resize((1024, 1024)).save(icon)
    licenses = assets / "licenses"
    licenses.mkdir(exist_ok=True)
    distributions = ["Pillow", "pyinstaller"] + (
        ["pyobjc-core", "pyobjc-framework-Cocoa"] if mac else ["pystray", "six"]
    )
    for name in distributions:
        distribution = importlib.metadata.distribution(name)
        for file in distribution.files or ():
            if any(part.lower().startswith(("license", "copying")) for part in file.parts):
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    shutil.copy2(source, licenses / f"{name}-{source.name}")
    arguments = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        "AcademicClipboard",
        "--icon",
        str(icon),
        "--paths",
        "src",
        "--add-data",
        f"LICENSE{os.pathsep}.",
        "--add-data",
        f"{licenses}{os.pathsep}licenses",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "numpy",
    ]
    if mac:
        arguments += [
            "--osx-bundle-identifier",
            "io.github.studyer-tang.academic-clipboard",
            "--exclude-module",
            "pystray",
            "--exclude-module",
            "Quartz",
        ]
    else:
        arguments += ["--hidden-import", "pystray._win32"]
    arguments.append("src/academic_clipboard/__main__.py")
    subprocess.run(arguments, check=True)
    if mac:
        bundle = Path("dist/AcademicClipboard.app")
        info_path = bundle / "Contents/Info.plist"
        info = plistlib.loads(info_path.read_bytes())
        info.update(
            CFBundleShortVersionString=__version__,
            CFBundleVersion=__version__,
            CFBundleDisplayName="Academic Clipboard",
            LSApplicationCategoryType="public.app-category.productivity",
        )
        info_path.write_bytes(plistlib.dumps(info))
        # Re-seal our own generated bundle after setting its version; this is ad-hoc, not Developer ID.
        subprocess.run(["codesign", "--force", "--sign", "-", str(bundle)], check=True)
    executable = (
        Path("dist/AcademicClipboard.app/Contents/MacOS/AcademicClipboard")
        if mac
        else Path("dist/AcademicClipboard/AcademicClipboard.exe")
    )
    report = Path("build/desktop-smoke.json").resolve()
    report.unlink(missing_ok=True)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PYTHON") and key not in {"TCL_LIBRARY", "TK_LIBRARY"}
    }
    # A download must work outside the checkout and without development runtime paths.
    with tempfile.TemporaryDirectory(prefix="academic-package-test-") as temporary:
        subprocess.run(
            [str(executable.resolve()), "self-test", "--report", str(report)],
            check=True,
            timeout=45,
            cwd=temporary,
            env=environment,
        )
    if not json.loads(report.read_text(encoding="utf-8"))["ok"]:
        raise SystemExit("Bundled desktop smoke test failed")
    machine = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
    name = f"AcademicClipboard-{__version__}-{'macOS' if mac else 'Windows'}-{machine}"
    if mac:
        stage = Path("build") / "dmg"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        subprocess.run(
            ["ditto", "dist/AcademicClipboard.app", str(stage / "AcademicClipboard.app")], check=True
        )
        (stage / "Applications").symlink_to("/Applications")
        artifact = Path("dist") / f"{name}.dmg"
        command = [
            "hdiutil",
            "create",
            "-volname",
            "Academic Clipboard",
            "-srcfolder",
            str(stage),
            "-ov",
            "-format",
            "UDZO",
            str(artifact),
        ]
        for attempt in range(3):
            result = subprocess.run(command, capture_output=True, text=True)
            print(result.stdout + result.stderr, end="")
            if result.returncode == 0:
                break
            if "Resource busy" not in result.stderr or attempt == 2:
                result.check_returncode()
            time.sleep(2 * (attempt + 1))
        subprocess.run(["hdiutil", "verify", str(artifact)], check=True)

    else:
        artifact = Path(shutil.make_archive(str(Path("dist") / name), "zip", "dist", "AcademicClipboard"))
    digest = hashlib.sha256()
    with artifact.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    artifact.with_suffix(artifact.suffix + ".sha256").write_text(
        f"{digest.hexdigest()}  {artifact.name}\n", encoding="ascii"
    )
    print(f"{artifact}: {artifact.stat().st_size / 1024**2:.1f} MiB")


if __name__ == "__main__":
    main()
