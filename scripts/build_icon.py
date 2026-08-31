from pathlib import Path

from academic_clipboard.tray import TrayController


def main() -> None:
    destination = Path("build-assets") / "academic-clipboard.ico"
    destination.parent.mkdir(parents=True, exist_ok=True)
    TrayController._create_icon().save(destination, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(destination)


if __name__ == "__main__":
    main()
