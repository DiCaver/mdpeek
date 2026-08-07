from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QByteArray, QMimeData, QRectF, Qt, QUrl
from PySide6.QtGui import (
    QAction,
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QTextBlockFormat,
    QTextDocument,
    QTextFormat,
    QTextFrameFormat,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox, QTextBrowser

from .style import (
    PANEL_KIND_PROPERTY,
    QUOTE_PANEL,
    apply_document_style,
    document_font,
    document_stylesheet,
    window_gutter,
)


EMPTY_MESSAGE = """# MDPeek

Press Ctrl+O or drag and drop a Markdown file here.

You can also pass its path on the command line:

    mdpeek README.md
"""


class MarkdownViewer(QTextBrowser):
    """Read-only browser with remote images and grouped document panels."""

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._pending_images: set[QUrl] = set()
        self._remote_images: dict[QUrl, QImage] = {}
        self._document_generation = 0

    def clear_remote_images(self) -> None:
        """Discard image state belonging to the previous document."""
        self._pending_images.clear()
        self._remote_images.clear()
        self._document_generation += 1

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
                generation = self._document_generation
                reply.finished.connect(
                    lambda reply=reply, url=url, generation=generation:
                    self._image_loaded(reply, url, generation)
                )
            return QByteArray()
        return super().loadResource(resource_type, url)

    def _image_loaded(self, reply: QNetworkReply, url: QUrl, generation: int) -> None:
        self._pending_images.discard(url)
        if (
            generation == self._document_generation
            and reply.error() == QNetworkReply.NetworkError.NoError
        ):
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
        self.current_path: Path | None = None
        self.last_open_error: OSError | UnicodeError | None = None
        self.setAcceptDrops(True)

        self.viewer = MarkdownViewer()
        viewer = self.viewer
        # Let the window own file drops even when the cursor is over the document.
        viewer.setAcceptDrops(False)
        viewer.setFrameShape(QTextBrowser.Shape.NoFrame)
        viewer_palette = viewer.palette()
        viewer_palette.setBrush(
            QPalette.ColorRole.Base, self.palette().brush(QPalette.ColorRole.Window)
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
        self._create_file_menu()
        self._update_gutter()

        if path is None:
            self._show_empty_document()
        elif markdown is not None:
            self._display_document(path, markdown)
        else:
            self.open_file(path)

    def _create_file_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.open_action = QAction("&Open…", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.show_open_dialog)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _show_empty_document(self) -> None:
        self.setWindowTitle("MDPeek")
        self.viewer.document().setBaseUrl(QUrl())
        self.viewer.setMarkdown(EMPTY_MESSAGE)
        apply_document_style(self.viewer.document(), self.viewer.palette(), EMPTY_MESSAGE)

    def _display_document(self, path: Path, markdown: str) -> None:
        resolved = path.resolve()
        self.viewer.clear_remote_images()
        self.viewer.document().setBaseUrl(QUrl.fromLocalFile(str(resolved.parent) + "/"))
        self.viewer.setMarkdown(markdown)
        apply_document_style(self.viewer.document(), self.viewer.palette(), markdown)
        self.viewer.verticalScrollBar().setValue(0)
        self.viewer.horizontalScrollBar().setValue(0)
        self.current_path = resolved
        self.setWindowTitle(f"{resolved.name} — MDPeek")

    def open_file(self, path: str | Path, *, show_error: bool = True) -> bool:
        """Read and display a UTF-8 file, preserving the document on failure."""
        candidate = Path(path)
        try:
            markdown = read_markdown(candidate)
        except (OSError, UnicodeError) as error:
            self.last_open_error = error
            if show_error:
                QMessageBox.critical(
                    self, "Could not open file",
                    f"MDPeek could not open:\n{candidate}\n\n{error}",
                )
            return False
        self.last_open_error = None
        self._display_document(candidate, markdown)
        return True

    def show_open_dialog(self) -> None:
        start = self.current_path.parent if self.current_path else Path.home()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Markdown file", str(start),
            "Markdown files (*.md *.markdown);;All files (*.*)",
        )
        if filename:
            self.open_file(filename)

    @staticmethod
    def dropped_markdown_path(mime_data: QMimeData) -> Path | None:
        """Return the one supported local Markdown file in drag data, if any."""
        if not mime_data.hasUrls():
            return None
        urls = mime_data.urls()
        if len(urls) != 1 or not urls[0].isLocalFile():
            return None
        path = Path(urls[0].toLocalFile())
        if not path.is_file() or path.suffix.lower() not in {".md", ".markdown"}:
            return None
        return path

    def dragEnterEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.dropped_markdown_path(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        path = self.dropped_markdown_path(event.mimeData())
        if path is not None and self.open_file(path):
            event.acceptProposedAction()
        else:
            event.ignore()

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
    app = QApplication(sys.argv[:1])
    window = MarkdownWindow()
    if args.file is not None and not window.open_file(args.file, show_error=False):
        print(
            f"mdpeek: could not open '{args.file}': {window.last_open_error}",
            file=sys.stderr,
        )
        return 2
    window.show()
    return app.exec()
