from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt, QUrl
from PySide6.QtGui import (
    QColor,
    QImage,
    QPainter,
    QPalette,
    QPen,
    QTextBlockFormat,
    QTextDocument,
    QTextFormat,
    QTextFrameFormat,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QApplication, QMainWindow, QTextBrowser

from .style import (
    PANEL_KIND_PROPERTY,
    QUOTE_PANEL,
    apply_document_style,
    document_font,
    document_stylesheet,
    window_gutter,
)


EMPTY_MESSAGE = """# MDPeek

Open a Markdown file by passing its path on the command line:

    mdpeek README.md
"""


class MarkdownViewer(QTextBrowser):
    """Read-only browser with remote images and grouped document panels."""

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._pending_images: set[QUrl] = set()
        self._remote_images: dict[QUrl, QImage] = {}

    def loadResource(self, resource_type: int, url: QUrl):  # type: ignore[no-untyped-def]
        if (
            resource_type == QTextDocument.ResourceType.ImageResource
            and url.scheme().lower() in {"http", "https"}
        ):
            if url in self._remote_images:
                return self._remote_images[url]
            if url not in self._pending_images:
                self._pending_images.add(url)
                reply = self._network.get(QNetworkRequest(url))
                reply.finished.connect(lambda reply=reply, url=url: self._image_loaded(reply, url))
            return QByteArray()
        return super().loadResource(resource_type, url)

    def _image_loaded(self, reply: QNetworkReply, url: QUrl) -> None:
        self._pending_images.discard(url)
        if reply.error() == QNetworkReply.NetworkError.NoError:
            image = QImage.fromData(reply.readAll())
            if not image.isNull():
                self._remote_images[url] = image
                self.document().addResource(
                    QTextDocument.ResourceType.ImageResource, url, image
                )
                self.document().markContentsDirty(0, self.document().characterCount())
                self.viewport().update()
        reply.deleteLater()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().color(QPalette.ColorRole.Base).lightness() < 128
        painter.setPen(QColor("#56616c" if dark else "#b8c0c8"))
        layout = self.document().documentLayout()
        for frame in self.document().rootFrame().childFrames():
            frame_format = QTextFrameFormat(frame.format())
            if frame_format.property(PANEL_KIND_PROPERTY) != QUOTE_PANEL:
                continue
            rect = layout.frameBoundingRect(frame).translated(
                -self.horizontalScrollBar().value(),
                -self.verticalScrollBar().value(),
            )
            x = round(rect.left() + frame_format.margin())
            painter.drawLine(x, round(rect.top() + 8), x, round(rect.bottom() - 8))

        # Qt renders checked Markdown task items as a boxed X. Paint a familiar
        # tick in the same marker position while retaining the read-only list.
        block = self.document().begin()
        while block.isValid():
            if block.blockFormat().marker() == QTextBlockFormat.MarkerType.Checked:
                rect = layout.blockBoundingRect(block)
                line = block.layout().lineAt(0)
                text_left = rect.left() + line.naturalTextRect().left()
                box = QRectF(
                    text_left - 17 - self.horizontalScrollBar().value(),
                    rect.top() + (rect.height() - 12) / 2
                    - self.verticalScrollBar().value(),
                    12,
                    12,
                )
                painter.fillRect(box.adjusted(-1, -1, 1, 1), self.palette().base())
                painter.setPen(QPen(QColor("#9da7b1" if dark else "#57606a"), 1))
                painter.drawRect(box)
                painter.setPen(QPen(QColor("#e6edf3" if dark else "#24292f"), 1.6))
                painter.drawLine(box.left() + 2.5, box.top() + 6.2, box.left() + 5.1, box.top() + 8.7)
                painter.drawLine(box.left() + 5.1, box.top() + 8.7, box.left() + 9.8, box.top() + 3.2)
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
