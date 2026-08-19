"""Resolution-independent application action icons."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


COPY_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#737b84" stroke-width="2" stroke-linejoin="round"><rect x="8" y="8" width="11" height="11" rx="1"/><path d="M16 8V5H5v11h3"/></g></svg>'''
SECTION_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#737b84" stroke-width="2" stroke-linecap="round"><path d="M5 6h14M5 11h9M5 16h6"/><path d="m15 16 2.5 2.5L21 14"/></g></svg>'''
CHECK_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" fill="none" stroke="#388a52" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'''


def svg_icon(data: bytes) -> QIcon:
    renderer = QSvgRenderer(QByteArray(data))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
