from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QPainter, QPalette, QTextFormat
from PySide6.QtWidgets import QApplication, QMainWindow, QTextBrowser

from .style import apply_document_style, document_font, document_stylesheet, window_gutter


EMPTY_MESSAGE = """# MDPeek

Open a Markdown file by passing its path on the command line:

    mdpeek README.md
"""


class MarkdownViewer(QTextBrowser):
    """Read-only browser with paint-only blockquote rules."""

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        dark = self.palette().color(QPalette.ColorRole.Base).lightness() < 128
        painter.setPen(QColor("#56616c" if dark else "#b8c0c8"))
        document_margin = self.document().documentMargin()
        x = round(document_margin + 3 - self.horizontalScrollBar().value())
        block = self.document().begin()
        while block.isValid():
            if block.blockFormat().property(QTextFormat.Property.BlockQuoteLevel):
                rect = self.document().documentLayout().blockBoundingRect(block)
                top = round(rect.top() - self.verticalScrollBar().value())
                bottom = round(rect.bottom() - self.verticalScrollBar().value())
                if bottom >= 0 and top <= self.viewport().height():
                    painter.drawLine(x, top, x, bottom)
            block = block.next()


def read_markdown(path: Path) -> str:
    """Return UTF-8 Markdown from a regular file."""
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    return path.read_text(encoding="utf-8")


class MarkdownWindow(QMainWindow):
    def __init__(self, path: Path | None = None, markdown: str | None = None) -> None:
        super().__init__()
        self.resize(900, 700)

        viewer = MarkdownViewer()
        viewer.setFrameShape(QTextBrowser.Shape.NoFrame)
        viewer_palette = viewer.palette()
        viewer_palette.setBrush(
            QPalette.ColorRole.Base,
            self.palette().brush(QPalette.ColorRole.Window),
        )
        viewer.setPalette(viewer_palette)
        viewer.setFont(document_font())
        viewer.document().setDefaultFont(document_font())
        viewer.document().setDefaultStyleSheet(document_stylesheet())
        viewer.setOpenExternalLinks(True)
        viewer.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.setCentralWidget(viewer)
        self._update_gutter()

        if path is None:
            self.setWindowTitle("MDPeek")
            viewer.setMarkdown(EMPTY_MESSAGE)
        else:
            self.setWindowTitle(f"{path.name} — MDPeek")
            viewer.document().setBaseUrl(QUrl.fromLocalFile(str(path.parent.resolve()) + "/"))
            viewer.setMarkdown(markdown or "")

        apply_document_style(viewer.document(), viewer.palette(), markdown or EMPTY_MESSAGE)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._update_gutter()

    def _update_gutter(self) -> None:
        gutter = window_gutter(self.width())
        viewer = self.centralWidget()
        if isinstance(viewer, QTextBrowser):
            viewer.setViewportMargins(gutter, gutter, gutter, gutter)


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
