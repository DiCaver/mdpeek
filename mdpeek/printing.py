"""Native print preview and paper-specific document preparation."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QMarginsF, QSizeF, QUrl
from PySide6.QtGui import (
    QColor,
    QImage,
    QPageLayout,
    QPalette,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextFrameFormat,
    QTextImageFormat,
)
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PySide6.QtWidgets import QWidget

from .style import CODE_PANEL, PANEL_KIND_PROPERTY, QUOTE_PANEL, apply_document_style


PRINT_MARGIN_MM = 18.0


def create_printer() -> QPrinter:
    """Create a printer using the system page size and restrained defaults."""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    layout = printer.pageLayout()
    layout.setOrientation(QPageLayout.Orientation.Portrait)
    layout.setUnits(QPageLayout.Unit.Millimeter)
    layout.setMargins(QMarginsF(*(PRINT_MARGIN_MM,) * 4))
    printer.setPageLayout(layout)
    return printer


def _copy_available_images(source: QTextDocument, target: QTextDocument) -> None:
    """Copy image resources already known to the live document, without I/O."""
    block = source.begin()
    copied: set[str] = set()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            image = QTextImageFormat(fragment.charFormat())
            name = image.name()
            if image.isValid() and name and name not in copied:
                url = QUrl(name)
                resource = source.resource(QTextDocument.ResourceType.ImageResource, url)
                resolved_url = source.baseUrl().resolved(url)
                if resource is None and resolved_url != url:
                    resource = source.resource(
                        QTextDocument.ResourceType.ImageResource, resolved_url
                    )
                if resource is not None:
                    target.addResource(QTextDocument.ResourceType.ImageResource, url, resource)
                    if resolved_url != url:
                        target.addResource(
                            QTextDocument.ResourceType.ImageResource, resolved_url, resource
                        )
                copied.add(name)
            iterator += 1
        block = block.next()


def _style_for_paper(document: QTextDocument, markdown: str) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#202124"))
    apply_document_style(document, palette, markdown)

    root_format = QTextFrameFormat(document.rootFrame().frameFormat())
    root_format.setBackground(QColor("#ffffff"))
    root_format.setMargin(0)
    root_format.setPadding(0)
    document.rootFrame().setFrameFormat(root_format)

    block = document.begin()
    while block.isValid():
        block_format = block.blockFormat()
        # Long code lines must wrap on paper instead of extending past the page.
        if block_format.property(QTextFormat.Property.BlockNonBreakableLines):
            block_format.setProperty(QTextFormat.Property.BlockNonBreakableLines, False)
        QTextCursor(block).setBlockFormat(block_format)

        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            char_format = fragment.charFormat()
            if char_format.isAnchor():
                char_format.setForeground(QColor("#0757a6"))
                char_format.setFontUnderline(True)
                cursor = QTextCursor(document)
                cursor.setPosition(fragment.position())
                cursor.setPosition(
                    fragment.position() + fragment.length(),
                    QTextCursor.MoveMode.KeepAnchor,
                )
                cursor.setCharFormat(char_format)
            iterator += 1
        block = block.next()

    for frame in document.rootFrame().childFrames():
        kind = frame.format().property(PANEL_KIND_PROPERTY)
        if kind in (CODE_PANEL, QUOTE_PANEL):
            frame_format = QTextFrameFormat(frame.frameFormat())
            frame_format.setBackground(QColor("#f4f5f6"))
            frame_format.setBorder(0.6)
            frame_format.setBorderBrush(QColor("#aeb4ba"))
            frame.setFrameFormat(frame_format)


def _constrain_images(document: QTextDocument, maximum_width: float) -> None:
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            image_format = QTextImageFormat(fragment.charFormat())
            if image_format.isValid() and image_format.name():
                url = QUrl(image_format.name())
                resource = document.resource(QTextDocument.ResourceType.ImageResource, url)
                if resource is None:
                    resource = document.resource(
                        QTextDocument.ResourceType.ImageResource,
                        document.baseUrl().resolved(url),
                    )
                size = getattr(resource, "size", lambda: QSizeF())()
                if not hasattr(size, "width"):
                    decoded = QImage.fromData(resource) if resource is not None else QImage()
                    size = decoded.size()
                width = image_format.width() or size.width()
                height = image_format.height() or size.height()
                if width > maximum_width and width > 0 and height > 0:
                    scale = maximum_width / width
                    image_format.setWidth(maximum_width)
                    image_format.setHeight(height * scale)
                    cursor = QTextCursor(document)
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(
                        fragment.position() + fragment.length(),
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    cursor.setCharFormat(image_format)
            iterator += 1
        block = block.next()


def prepare_printable_document(
    live_document: QTextDocument, markdown: str, printer: QPrinter
) -> QTextDocument:
    """Return an independent, complete document laid out for ``printer``."""
    document = QTextDocument()
    document.setBaseUrl(live_document.baseUrl())
    document.setMarkdown(markdown)
    # setMarkdown clears the document's resource cache, so transfer resources
    # only after the printable structure exists.
    _copy_available_images(live_document, document)
    _style_for_paper(document, markdown)

    # QTextDocument layout units are typographic points, independent of the
    # printer's device DPI. QPrinter performs the final device scaling.
    page_rect = printer.pageLayout().paintRect(QPageLayout.Unit.Point)
    page_size = QSizeF(page_rect.size())
    document.setPageSize(page_size)
    _constrain_images(document, max(1.0, page_size.width()))
    document.adjustSize()
    document.setPageSize(page_size)
    return document


def show_print_preview(
    parent: QWidget,
    title: str,
    document_factory: Callable[[QPrinter], QTextDocument],
) -> int:
    """Run Qt's native preview, preparing against its current printer layout."""
    printer = create_printer()
    preview = QPrintPreviewDialog(printer, parent)
    preview.setWindowTitle(title)

    def paint(requested_printer: QPrinter) -> None:
        document = document_factory(requested_printer)
        document.print_(requested_printer)

    preview.paintRequested.connect(paint)
    return preview.exec()
