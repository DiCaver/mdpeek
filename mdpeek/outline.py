"""Qt-native document outline built from MDPeek's rendered heading regions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem, QWidget

from .document_regions import DocumentRegions, HeadingRegion


UNTITLED_HEADING = "(Untitled heading)"
NO_HEADINGS = "No headings in this document"


def heading_parent_indexes(headings: tuple[HeadingRegion, ...]) -> list[int | None]:
    """Return the nearest preceding lower-level heading for every heading."""
    parents: list[int | None] = []
    ancestors: list[tuple[int, int]] = []
    for index, heading in enumerate(headings):
        while ancestors and ancestors[-1][0] >= heading.level:
            ancestors.pop()
        parents.append(ancestors[-1][1] if ancestors else None)
        ancestors.append((heading.level, index))
    return parents


class DocumentOutline(QDockWidget):
    """Collapsible heading tree; it never parses Markdown independently."""

    headingActivated = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Outline", parent)
        self.setObjectName("documentOutline")
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.setMinimumWidth(180)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tree.setStyleSheet("QTreeWidget { border: 0; padding: 4px; }")
        self.setWidget(self.tree)
        self._items: list[QTreeWidgetItem] = []
        self._regions = DocumentRegions()
        self._updating = False
        self.tree.itemClicked.connect(self._item_clicked)

    @property
    def regions(self) -> DocumentRegions:
        return self._regions

    def set_regions(self, regions: DocumentRegions, *, empty_document: bool = False) -> None:
        self._regions = regions
        self._items = []
        self.tree.clear()
        if empty_document:
            return
        if not regions.headings:
            item = QTreeWidgetItem([NO_HEADINGS])
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.tree.addTopLevelItem(item)
            return
        parents = heading_parent_indexes(regions.headings)
        for index, (heading, parent_index) in enumerate(zip(regions.headings, parents)):
            title = heading.title.strip() or UNTITLED_HEADING
            item = QTreeWidgetItem([title])
            item.setToolTip(0, title)
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            if parent_index is None:
                self.tree.addTopLevelItem(item)
            else:
                self._items[parent_index].addChild(item)
            self._items.append(item)
        self.tree.expandAll()
        self.set_active_index(0)

    def set_active_index(self, index: int | None) -> None:
        item = self._items[index] if index is not None and 0 <= index < len(self._items) else None
        if self.tree.currentItem() is item:
            return
        self._updating = True
        self.tree.setCurrentItem(item)
        if item is not None:
            # Reveal without expanding branches the user deliberately collapsed.
            self.tree.scrollToItem(item, QTreeWidget.ScrollHint.EnsureVisible)
        self._updating = False

    def _item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._updating:
            return
        index = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self.headingActivated.emit(index)
