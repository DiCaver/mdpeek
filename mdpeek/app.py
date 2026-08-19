from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QByteArray, QFileSystemWatcher, QMimeData, QPoint, QRect, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QImage,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QTextBlockFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextFrameFormat,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QFileDialog, QMainWindow, QMenu, QMessageBox, QTextBrowser, QToolButton, QVBoxLayout

from .clipboard import html_source_mime_data, plain_mime_data
from .markdown_copy import markdown_mime_data
from .document_regions import CodeRegion, DocumentRegions, HeadingRegion, build_document_regions
from .outline import DocumentOutline
from .navigation import NavigationHistory, normalize_path
from .printing import prepare_printable_document, show_print_preview as open_print_preview, suggested_pdf_path
from .content import safe_markdown
from .icons import CHECK_SVG, COPY_SVG, SECTION_SVG, svg_icon
from .instance import InstanceServer, forward_path
from .resources import application_icon_path
from .version import __version__

from .style import (
    PANEL_KIND_PROPERTY,
    QUOTE_PANEL,
    apply_document_style,
    document_font,
    document_stylesheet,
    window_gutter,
)


EMPTY_MESSAGE = """# MDPeek

Open a Markdown file to start reading.

- **Ctrl+O** — Open a file
- Drag and drop a Markdown file here
- **F1** — Open Help
"""

HELP_MARKDOWN = """# MDPeek Help

Open a Markdown file with **Ctrl+O**, or drag and drop it onto MDPeek. Files changed by another application refresh automatically.

## Reading and navigation

- Select text with the mouse. **Ctrl+A** selects all content.
- **Ctrl+C** copies plain text, **Ctrl+Shift+M** copies Markdown, and **Ctrl+Shift+C** copies HTML.
- Use a heading's section action to select everything under that heading.
- **Ctrl+F** finds text. **Alt+Left** and **Alt+Right** navigate file history.
- **Ctrl+H** shows or hides the Outline.
- Use the copy action in a code block to copy its exact contents.

## Printing

Press **Ctrl+P** to open Print Preview. Choose a physical printer or a PDF printer to save a PDF.
"""


def initial_window_geometry(work_area: QRect) -> QRect:
    width = min(800, work_area.width())
    height = min(1000, work_area.height())
    return QRect(work_area.x() + (work_area.width() - width) // 2,
                 work_area.y() + (work_area.height() - height) // 2,
                 width, height)


class MarkdownViewer(QTextBrowser):
    """Read-only browser with remote images and grouped document panels."""

    sectionRequested = Signal(object)
    codeCopyRequested = Signal(object)
    visiblePositionChanged = Signal()

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self._network = QNetworkAccessManager(self)
        self._pending_images: set[QUrl] = set()
        self._remote_images: dict[QUrl, QImage] = {}
        self._document_generation = 0
        self.regions = DocumentRegions()
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self._hovered_heading: HeadingRegion | None = None
        self._hovered_code: CodeRegion | None = None
        self.setCursorWidth(0)
        self._section_button = self._overlay_button(SECTION_SVG, "Select this section")
        self._section_button.clicked.connect(self._request_hovered_section)
        self._code_button = self._overlay_button(COPY_SVG, "Copy code")
        self._code_button.clicked.connect(self._request_hovered_code)
        self.verticalScrollBar().valueChanged.connect(self._visible_position_changed)
        self.horizontalScrollBar().valueChanged.connect(self._position_overlays)

    def _overlay_button(self, icon_data: bytes, tooltip: str) -> QToolButton:
        button = QToolButton(self.viewport())
        button.setIcon(svg_icon(icon_data))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setAutoRaise(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(24, 24)
        button.setStyleSheet(
            "QToolButton { background: palette(base); "
            "border: 1px solid palette(midlight); border-radius: 4px; }"
            "QToolButton:hover { color: palette(text); border-color: palette(mid); }"
        )
        button.hide()
        return button

    def set_document_regions(self, regions: DocumentRegions) -> None:
        self.regions = regions
        self._hovered_heading = None
        self._hovered_code = None
        self._section_button.hide()
        self._code_button.hide()

    def _request_hovered_section(self) -> None:
        if self._hovered_heading is not None:
            self.sectionRequested.emit(self._hovered_heading)

    def _request_hovered_code(self) -> None:
        if self._hovered_code is not None:
            self.codeCopyRequested.emit(self._hovered_code)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().mouseMoveEvent(event)
        cursor = self.cursorForPosition(event.position().toPoint())
        block = cursor.block()
        level = block.blockFormat().headingLevel()
        self._hovered_heading = next(
            (region for region in self.regions.headings
             if level and region.rendered_start == block.position()), None
        )
        self._hovered_code = self.regions.code_at(cursor.position())
        self._position_overlays()

    def leaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().leaveEvent(event)
        if not self._section_button.underMouse():
            self._hovered_heading = None
            self._section_button.hide()
        if not self._code_button.underMouse():
            self._hovered_code = None
            self._code_button.hide()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._position_overlays()
        self.visiblePositionChanged.emit()

    def _visible_position_changed(self) -> None:
        self._position_overlays()
        self.visiblePositionChanged.emit()

    def _position_overlays(self) -> None:
        if self._hovered_heading is not None:
            block = self.document().findBlock(self._hovered_heading.rendered_start)
            rect = self.document().documentLayout().blockBoundingRect(block)
            line = block.layout().lineAt(0)
            x = rect.left() + line.naturalTextRect().right() + 8 - self.horizontalScrollBar().value()
            x = min(x, self.viewport().width() - self._section_button.width() - 4)
            y = rect.top() + (rect.height() - self._section_button.height()) / 2 - self.verticalScrollBar().value()
            self._section_button.move(round(max(2, x)), round(y))
            self._section_button.show()
            self._section_button.raise_()
        else:
            self._section_button.hide()
        if self._hovered_code is not None:
            cursor = self.textCursor()
            cursor.setPosition(self._hovered_code.rendered_start)
            frame = cursor.currentFrame()
            rect = self.document().documentLayout().frameBoundingRect(frame)
            x = rect.right() - self._code_button.width() - 5 - self.horizontalScrollBar().value()
            y = rect.top() + 5 - self.verticalScrollBar().value()
            self._code_button.move(round(max(2, min(x, self.viewport().width() - 28))), round(y))
            self._code_button.show()
            self._code_button.raise_()
        else:
            self._code_button.hide()

    def show_copied_feedback(self) -> None:
        self._code_button.setIcon(svg_icon(CHECK_SVG))
        self._code_button.setToolTip("Copied")
        QTimer.singleShot(1200, self._reset_code_feedback)

    def _reset_code_feedback(self) -> None:
        self._code_button.setIcon(svg_icon(COPY_SVG))
        self._code_button.setToolTip("Copy code")

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
        icon_path = application_icon_path()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setMinimumSize(480, 560)
        screen = QApplication.primaryScreen()
        self.setGeometry(initial_window_geometry(screen.availableGeometry()) if screen else QRect(0, 0, 800, 1000))
        self.current_path: Path | None = None
        self.source_markdown = ""
        self.last_open_error: OSError | UnicodeError | None = None
        self.history = NavigationHistory()
        self._scroll_restore_generation = 0
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._file_changed)
        self._watcher.directoryChanged.connect(self._file_changed)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(180)
        self._refresh_timer.timeout.connect(self._reload_watched_file)
        self._refresh_attempts = 0
        # Retain transferred wrappers for the window lifetime. On Windows,
        # collecting a previous PySide QMimeData can clear a newer clipboard
        # payload asynchronously.
        self._clipboard_data: list[QMimeData] = []
        self.setAcceptDrops(True)

        self.viewer = MarkdownViewer()
        viewer = self.viewer
        # Let the window own file drops even when the cursor is over the document.
        viewer.setAcceptDrops(False)
        viewer.setMinimumWidth(320)
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
        self._create_edit_menu()
        self._create_view_menu()
        self._create_help_menu()
        viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        viewer.customContextMenuRequested.connect(self._show_context_menu)
        viewer.selectionChanged.connect(self._update_selection_actions)
        viewer.cursorPositionChanged.connect(self._update_region_actions)
        viewer.sectionRequested.connect(self.select_section)
        viewer.codeCopyRequested.connect(self.copy_code_region)
        viewer.visiblePositionChanged.connect(self._update_active_outline_item)
        self._update_gutter()

        if path is None:
            self._show_empty_document()
        elif markdown is not None:
            self._display_document(path, markdown)
            self.history.add(path)
            self._update_navigation_actions()
        else:
            self.open_file(path)

    def _create_view_menu(self) -> None:
        self.outline = DocumentOutline(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.outline)
        self.resizeDocks([self.outline], [240], Qt.Orientation.Horizontal)
        menu = self.menuBar().addMenu("&View")
        self.outline_action = self.outline.toggleViewAction()
        self.outline_action.setText("&Outline")
        self.outline_action.setShortcut(QKeySequence("Ctrl+H"))
        menu.addAction(self.outline_action)
        self.outline.headingActivated.connect(self._navigate_to_heading)
        self.outline.visibilityChanged.connect(
            lambda visible: QTimer.singleShot(0, self._update_active_outline_item) if visible else None
        )
        self.outline.hide()

    def _create_help_menu(self) -> None:
        menu = self.menuBar().addMenu("&Help")
        self.help_action = QAction("&?  MDPeek Help", self)
        self.help_action.setShortcut(QKeySequence(Qt.Key.Key_F1))
        self.help_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.help_action.triggered.connect(self.show_help)
        menu.addAction(self.help_action)

    def show_help(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("MDPeek Help")
        dialog.setModal(True)
        dialog.resize(620, 560)
        layout = QVBoxLayout(dialog)
        content = QTextBrowser(dialog)
        content.setReadOnly(True)
        content.setCursorWidth(0)
        content.setMarkdown(HELP_MARKDOWN)
        layout.addWidget(content)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _create_file_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.back_action = QAction("&Back", self)
        self.back_action.setShortcut(QKeySequence.StandardKey.Back)
        self.back_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.back_action.triggered.connect(self.go_back)
        file_menu.addAction(self.back_action)
        self.forward_action = QAction("&Forward", self)
        self.forward_action.setShortcut(QKeySequence.StandardKey.Forward)
        self.forward_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.forward_action.triggered.connect(self.go_forward)
        file_menu.addAction(self.forward_action)
        file_menu.addSeparator()
        self.open_action = QAction("&Open…", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.show_open_dialog)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        self.print_action = QAction("&Print…", self)
        self.print_action.setShortcut(QKeySequence.StandardKey.Print)
        self.print_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.print_action.setEnabled(False)
        self.print_action.triggered.connect(self.show_print_preview)
        file_menu.addAction(self.print_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        self._update_navigation_actions()

    def _update_navigation_actions(self) -> None:
        self.back_action.setEnabled(self.history.can_go_back)
        self.forward_action.setEnabled(self.history.can_go_forward)

    def _create_edit_menu(self) -> None:
        menu = self.menuBar().addMenu("&Edit")
        self.copy_plain_action = QAction("Copy as &Plain Text", self)
        self.copy_plain_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_plain_action.triggered.connect(self.copy_as_plain_text)
        menu.addAction(self.copy_plain_action)
        self.copy_html_action = QAction("Copy as &HTML", self)
        self.copy_html_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        self.copy_html_action.triggered.connect(self.copy_as_html)
        menu.addAction(self.copy_html_action)
        self.copy_markdown_action = QAction("Copy as &Markdown", self)
        self.copy_markdown_action.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self.copy_markdown_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.copy_markdown_action.triggered.connect(self.copy_as_markdown)
        menu.addAction(self.copy_markdown_action)
        menu.addSeparator()
        self.select_section_action = QAction("Select Current &Section", self)
        self.select_section_action.triggered.connect(self.select_current_section)
        menu.addAction(self.select_section_action)
        self.copy_code_action = QAction("Copy Current Code &Block", self)
        self.copy_code_action.triggered.connect(self.copy_current_code_block)
        menu.addAction(self.copy_code_action)
        menu.addSeparator()
        self.select_all_action = QAction("Select &All", self)
        self.select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.select_all_action.triggered.connect(self.viewer.selectAll)
        menu.addAction(self.select_all_action)
        self._update_selection_actions()

    def _update_selection_actions(self) -> None:
        selected = self.viewer.textCursor().hasSelection()
        self.copy_plain_action.setEnabled(selected)
        self.copy_html_action.setEnabled(selected)
        self.copy_markdown_action.setEnabled(selected and self.current_path is not None)
        self.select_all_action.setEnabled(bool(self.viewer.document().toPlainText()))
        self._update_region_actions()

    def _cursor_region_position(self) -> int:
        cursor = self.viewer.textCursor()
        return cursor.selectionStart() if cursor.hasSelection() else cursor.position()

    def _update_region_actions(self) -> None:
        position = self._cursor_region_position()
        self.select_section_action.setEnabled(self.viewer.regions.heading_at(position) is not None)
        self.copy_code_action.setEnabled(self.viewer.regions.code_at(position) is not None)

    def select_current_section(self) -> None:
        region = self.viewer.regions.heading_at(self._cursor_region_position())
        if region is not None:
            self.select_section(region)

    def select_section(self, region: HeadingRegion) -> None:
        cursor = self.viewer.textCursor()
        # Build the selection backwards so its active end is the heading.
        # QTextBrowser then reveals the beginning rather than scrolling to the
        # bottom of a long section.
        cursor.setPosition(region.rendered_end)
        cursor.setPosition(region.rendered_start, QTextCursor.MoveMode.KeepAnchor)
        self.viewer.setTextCursor(cursor)
        self.viewer.ensureCursorVisible()
        QTimer.singleShot(0, self._update_active_outline_item)

    def _navigate_to_heading(self, index: int) -> None:
        if not 0 <= index < len(self.viewer.regions.headings):
            return
        region = self.viewer.regions.headings[index]
        block = self.viewer.document().findBlock(region.rendered_start)
        top = self.viewer.document().documentLayout().blockBoundingRect(block).top()
        self.viewer.verticalScrollBar().setValue(max(0, round(top - 12)))
        self.outline.set_active_index(index)

    def _top_visible_position(self) -> int:
        return self.viewer.cursorForPosition(QPoint(0, 8)).position()

    def _update_active_outline_item(self) -> None:
        headings = self.viewer.regions.headings
        if not headings:
            self.outline.set_active_index(None)
            return
        scrollbar = self.viewer.verticalScrollBar()
        if scrollbar.maximum() > 0 and scrollbar.value() >= scrollbar.maximum():
            self.outline.set_active_index(len(headings) - 1)
            return
        position = self._top_visible_position()
        region = self.viewer.regions.heading_at(position)
        if region is None:
            index = 0
        else:
            index = headings.index(region)
        self.outline.set_active_index(index)

    def copy_current_code_block(self) -> None:
        region = self.viewer.regions.code_at(self._cursor_region_position())
        if region is not None:
            self.copy_code_region(region)

    def copy_code_region(self, region: CodeRegion) -> None:
        data = QMimeData()
        data.setText(region.code)
        self._set_clipboard_data(data)
        self.viewer.show_copied_feedback()

    def _set_clipboard_data(self, data: QMimeData) -> None:
        """Replace clipboard data reliably across PySide Windows versions."""
        clipboard = QApplication.clipboard()
        clipboard.clear()
        self._clipboard_data.append(data)
        clipboard.setMimeData(data)

    def copy_as_plain_text(self) -> None:
        data = plain_mime_data(self.viewer.textCursor())
        if data is not None:
            self._set_clipboard_data(data)

    def copy_as_html(self) -> None:
        data = html_source_mime_data(self.viewer.textCursor())
        if data is not None:
            self._set_clipboard_data(data)

    def copy_as_markdown(self) -> None:
        data = markdown_mime_data(
            self.viewer.textCursor(), self.source_markdown, self.viewer.regions
        )
        if data is not None:
            self._set_clipboard_data(data)

    def _context_menu(self, position: QPoint) -> QMenu:
        menu = QMenu(self.viewer)
        menu.addAction(self.copy_plain_action)
        menu.addAction(self.copy_html_action)
        menu.addAction(self.copy_markdown_action)
        menu.addSeparator()
        menu.addAction(self.select_section_action)
        menu.addAction(self.copy_code_action)
        menu.addSeparator()
        menu.addAction(self.select_all_action)
        return menu

    def _show_context_menu(self, position: QPoint) -> None:
        menu = self._context_menu(position)
        menu.exec(self.viewer.viewport().mapToGlobal(position))

    def _show_empty_document(self) -> None:
        self.setWindowTitle("MDPeek")
        self.viewer.document().setBaseUrl(QUrl())
        self.viewer.setMarkdown(EMPTY_MESSAGE)
        apply_document_style(self.viewer.document(), self.viewer.palette(), EMPTY_MESSAGE)
        self.viewer.set_document_regions(DocumentRegions())
        self.outline.set_regions(DocumentRegions(), empty_document=True)
        self.source_markdown = ""
        self.current_path = None
        self.print_action.setEnabled(False)
        self._update_selection_actions()

    def _display_document(self, path: Path, markdown: str) -> None:
        resolved = normalize_path(path)
        rendered_markdown = safe_markdown(markdown)
        self._scroll_restore_generation += 1
        self.viewer.clear_remote_images()
        self.viewer.document().setBaseUrl(QUrl.fromLocalFile(str(resolved.parent) + "/"))
        self.viewer.setMarkdown(rendered_markdown)
        apply_document_style(self.viewer.document(), self.viewer.palette(), rendered_markdown)
        regions = build_document_regions(self.viewer.document(), rendered_markdown)
        self.viewer.set_document_regions(regions)
        self.outline.set_regions(regions)
        self.viewer.verticalScrollBar().setValue(0)
        self.viewer.horizontalScrollBar().setValue(0)
        self.current_path = resolved
        self.print_action.setEnabled(True)
        self.source_markdown = markdown
        self.setWindowTitle(f"{resolved.name} — MDPeek")
        self._update_selection_actions()
        self._watch_file(resolved)

    def show_print_preview(self) -> None:
        """Preview the complete currently displayed document without mutating it."""
        if self.current_path is None:
            return
        title = f"Print Preview — {self.current_path.name}"
        open_print_preview(
            self,
            title,
            lambda printer: prepare_printable_document(
                self.viewer.document(), safe_markdown(self.source_markdown), printer
            ),
            suggested_pdf_path(self.current_path),
        )

    def _watch_file(self, path: Path) -> None:
        watched = self._watcher.files() + self._watcher.directories()
        if watched:
            self._watcher.removePaths(watched)
        self._watcher.addPath(str(path.parent))
        if path.is_file():
            self._watcher.addPath(str(path))

    def _file_changed(self, _path: str) -> None:
        self._refresh_attempts = 0
        self._refresh_timer.start()

    def _reload_watched_file(self) -> None:
        path = self.current_path
        if path is None:
            return
        try:
            markdown = read_markdown(path)
        except (OSError, UnicodeError):
            self._refresh_attempts += 1
            if self._refresh_attempts < 5:
                self._refresh_timer.start(200)
            else:
                self.statusBar().showMessage(
                    "The current file is unavailable; showing the last loaded version.", 8000
                )
                self._watch_file(path)
            return
        position = self.viewer.verticalScrollBar().value()
        self._display_document(path, markdown)
        self._restore_vertical_position(position)
        self.statusBar().showMessage("Updated from disk", 2000)

    def _restore_vertical_position(self, position: int) -> None:
        """Restore now and once more after Qt completes deferred layout."""
        generation = self._scroll_restore_generation

        def restore() -> None:
            if generation != self._scroll_restore_generation:
                return
            scrollbar = self.viewer.verticalScrollBar()
            scrollbar.setValue(max(scrollbar.minimum(), min(int(position), scrollbar.maximum())))
            self._update_active_outline_item()
            self.viewer.viewport().update()

        restore()
        QTimer.singleShot(0, restore)

    def open_file(self, path: str | Path, *, show_error: bool = True) -> bool:
        """Read and display a UTF-8 file, preserving the document on failure."""
        candidate = normalize_path(path)
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
        refresh = self.history.current is not None and self.history.current.path == candidate
        saved_position = self.viewer.verticalScrollBar().value()
        self.history.record_current_position(saved_position)
        self._display_document(candidate, markdown)
        if refresh:
            self._restore_vertical_position(saved_position)
        else:
            self.history.add(candidate)
        self._update_navigation_actions()
        return True

    def _navigate_history(self, offset: int, *, show_error: bool = True) -> bool:
        target_index = self.history.target_index(offset)
        if target_index is None:
            self._update_navigation_actions()
            return False
        target = self.history.entries[target_index]
        try:
            markdown = read_markdown(target.path)
        except (OSError, UnicodeError) as error:
            self.last_open_error = error
            if show_error:
                QMessageBox.critical(
                    self, "Could not open file",
                    f"MDPeek could not open:\n{target.path}\n\n{error}",
                )
            self._update_navigation_actions()
            return False
        self.last_open_error = None
        self.history.record_current_position(self.viewer.verticalScrollBar().value())
        self._display_document(target.path, markdown)
        self.history.move_to(target_index)
        self._restore_vertical_position(target.vertical_position)
        self._update_navigation_actions()
        return True

    def go_back(self) -> bool:
        return self._navigate_history(-1)

    def go_forward(self) -> bool:
        return self._navigate_history(1)

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


def startup_path_error(path: Path) -> str | None:
    """Describe an invalid Explorer/command-line target without opening it."""
    if path.is_dir():
        return "The selected path is a directory, not a Markdown file."
    if path.suffix.lower() not in {".md", ".markdown"}:
        return "MDPeek opens .md and .markdown files."
    if not path.is_file():
        return "The selected Markdown file does not exist or is not a regular file."
    return None


def main(argv: Sequence[str] | None = None) -> int:
    args, unexpected = build_parser().parse_known_args(argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("MDPeek")
    app.setApplicationDisplayName("MDPeek")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("MDPeek contributors")
    icon_path = application_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))
    if forward_path(args.file):
        return 0
    window = MarkdownWindow()

    def receive(path: Path | None) -> None:
        if path is not None:
            error = startup_path_error(path)
            if error is None:
                window.open_file(path)
            else:
                QMessageBox.critical(
                    window, "Could not open file",
                    f"MDPeek could not open:\n{path}\n\n{error}",
                )
        if window.isMinimized():
            window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()

    server = InstanceServer(receive, app)
    server.start()
    window.show()
    if unexpected:
        QMessageBox.critical(
            window,
            "Could not open file",
            "MDPeek accepts one Markdown filepath. Unexpected arguments:\n\n"
            + " ".join(unexpected),
        )
    elif args.file is not None:
        error = startup_path_error(args.file)
        if error is None and not window.open_file(args.file, show_error=False):
            error = str(window.last_open_error)
        if error is not None:
            QMessageBox.critical(
                window,
                "Could not open file",
                f"MDPeek could not open:\n{args.file}\n\n{error}",
            )
    return app.exec()
