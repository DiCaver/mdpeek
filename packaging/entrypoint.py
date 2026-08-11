"""PyInstaller entry point; package execution remains mdpeek.__main__."""

from mdpeek.app import main


if __name__ == "__main__":
    raise SystemExit(main())
