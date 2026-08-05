from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import QApplication, QMainWindow, QTextBrowser


EMPTY_MESSAGE = """# MDPeek

Open a Markdown file by passing its path on the command line:

    mdpeek README.md
"""


def read_markdown(path: Path) -> str:
    """Return UTF-8 Markdown from a regular file."""
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    return path.read_text(encoding="utf-8")


class MarkdownWindow(QMainWindow):
    def __init__(self, path: Path | None = None, markdown: str | None = None) -> None:
        super().__init__()
        self.resize(900, 700)

        viewer = QTextBrowser()
        viewer_font = viewer.font()
        viewer_font.setPointSize(max(viewer_font.pointSize(), 11))
        viewer.setFont(viewer_font)
        viewer.setOpenExternalLinks(True)
        viewer.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.setCentralWidget(viewer)

        if path is None:
            self.setWindowTitle("MDPeek")
            viewer.setMarkdown(EMPTY_MESSAGE)
        else:
            self.setWindowTitle(f"{path.name} — MDPeek")
            viewer.document().setBaseUrl(QUrl.fromLocalFile(str(path.parent.resolve()) + "/"))
            viewer.setMarkdown(markdown or "")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="View a Markdown file.")
    parser.add_argument("file", nargs="?", type=Path, help="Markdown file to open")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    markdown = None
    if args.file is not None:
        try:
            markdown = read_markdown(args.file)
        except (OSError, UnicodeError) as error:
            print(f"mdpeek: could not open '{args.file}': {error}", file=sys.stderr)
            return 2

    app = QApplication(sys.argv[:1])
    window = MarkdownWindow(args.file, markdown)
    window.show()
    return app.exec()
