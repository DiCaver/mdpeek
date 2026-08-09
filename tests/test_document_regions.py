from __future__ import annotations

import unittest
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from mdpeek.app import MarkdownWindow
from mdpeek.document_regions import HeadingRegion, scan_source_code_fences, scan_source_headings
from mdpeek.outline import NO_HEADINGS, UNTITLED_HEADING, heading_parent_indexes


class SourceRegionTests(unittest.TestCase):
    def test_outline_hierarchy_handles_siblings_nesting_and_skipped_levels(self) -> None:
        headings = tuple(
            HeadingRegion(level, index, index + 1, title=title)
            for index, (level, title) in enumerate([
                (1, "Root"), (2, "Setup"), (3, "Windows"), (3, "Linux"),
                (2, "Usage"), (4, "Advanced"), (1, "Other"),
            ])
        )
        self.assertEqual(heading_parent_indexes(headings), [None, 0, 1, 1, 0, 4, None])

    def test_outline_constants_are_quiet_fallbacks(self) -> None:
        self.assertEqual(UNTITLED_HEADING, "(Untitled heading)")
        self.assertEqual(NO_HEADINGS, "No headings in this document")

    def test_heading_scanner_ignores_fences_and_supports_repeated_and_setext(self) -> None:
        source = "# Same\n\n```\n## Not a heading\n```\nSame\n----\n# Same\n"
        self.assertEqual([h.level for h in scan_source_headings(source)], [1, 2, 1])

    def test_fence_scanner_preserves_exact_raw_code(self) -> None:
        source = "  ```python extra\r\n    indented\r\n  \r\n  <>& \'\" \\ č\r\n  ```\r\n"
        fence = scan_source_code_fences(source)[0]
        self.assertEqual(fence.language, "python")
        self.assertEqual(fence.code, "  indented\r\n\r\n<>& \'\" \\ č\r\n")

    def test_unknown_unlabelled_identical_and_unclosed_fences(self) -> None:
        source = "```mystery\nsame\n```\n```\nsame\n```\n```text\nno final newline"
        fences = scan_source_code_fences(source)
        self.assertEqual([f.language for f in fences], ["mystery", None, "text"])
        self.assertEqual([f.code for f in fences], ["same\n", "same\n", "no final newline"])

class RenderedRegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.windows: list[MarkdownWindow] = []

    def window(self, source: str) -> MarkdownWindow:
        window = MarkdownWindow(Path("regions.md"), source)
        self.windows.append(window)
        return window

    def selected(self, window: MarkdownWindow, heading_index: int) -> str:
        window.select_section(window.viewer.regions.headings[heading_index])
        return window.viewer.textCursor().selectedText().replace("\u2029", "\n")

    def test_h2_includes_nested_levels_and_stops_at_next_h2(self) -> None:
        window = self.window("# Root\n## Install\nintro\n### Windows\nwin\n###### Detail\ndeep\n## Usage\nuse")
        selected = self.selected(window, 1)
        for text in ("Install", "intro", "Windows", "win", "Detail", "deep"):
            self.assertIn(text, selected)
        self.assertNotIn("Usage", selected)

    def test_outline_preserves_titles_repeats_unicode_setext_and_empty(self) -> None:
        long_title = "Very long " * 20
        window = self.window(f"# Same\n# Same\nČebelica\n=========\n#\n# {long_title}")
        titles = [item.text(0) for item in window.outline._items]
        self.assertEqual(titles[:4], ["Same", "Same", "Čebelica", UNTITLED_HEADING])
        self.assertEqual(titles[4], long_title.strip())
        self.assertEqual(window.outline._items[4].toolTip(0), long_title.strip())

    def test_no_headings_and_welcome_outline_states(self) -> None:
        window = self.window("plain text")
        self.assertEqual(window.outline.tree.topLevelItem(0).text(0), NO_HEADINGS)
        empty = MarkdownWindow()
        self.windows.append(empty)
        self.assertEqual(empty.outline.tree.topLevelItemCount(), 0)

    def test_outline_navigation_preserves_selection_and_distinguishes_repeats(self) -> None:
        source = "# Same\nselected body\n\n" + "\n\n".join(f"filler {n}" for n in range(40)) + "\n# Same\nfinal"
        window = self.window(source)
        window.resize(700, 260)
        window.show()
        self.app.processEvents()
        selection = window.viewer.document().find("selected body")
        window.viewer.setTextCursor(selection)
        before = (selection.selectionStart(), selection.selectionEnd())
        window._navigate_to_heading(1)
        self.app.processEvents()
        after = window.viewer.textCursor()
        self.assertEqual((after.selectionStart(), after.selectionEnd()), before)
        self.assertGreater(window.viewer.verticalScrollBar().value(), 0)
        self.assertIs(window.outline.tree.currentItem(), window.outline._items[1])
        window._navigate_to_heading(0)
        self.assertEqual(window.viewer.verticalScrollBar().value(), 0)

    def test_scroll_updates_deepest_active_item_without_navigation_feedback(self) -> None:
        source = "# Root\n\n" + "\n\n".join(f"intro {n}" for n in range(25)) + "\n## Child\n### Deep\nbody"
        window = self.window(source)
        window.resize(700, 240)
        window.show()
        self.app.processEvents()
        activated = QSignalSpy(window.outline.headingActivated)
        window.viewer.verticalScrollBar().setValue(window.viewer.verticalScrollBar().maximum())
        self.app.processEvents()
        self.assertIs(window.outline.tree.currentItem(), window.outline._items[2])
        self.assertEqual(activated.count(), 0)

    def test_outline_action_visibility_lifecycle_and_failed_open(self) -> None:
        window = self.window("# First")
        window.show()
        self.app.processEvents()
        self.assertTrue(window.outline_action.isChecked())
        QTest.keyClick(window, Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertFalse(window.outline.isVisible())
        self.assertFalse(window.outline_action.isChecked())
        QTest.keyClick(window, Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertTrue(window.outline.isVisible())
        old_items = list(window.outline._items)
        self.assertFalse(window.open_file("tests/fixtures/missing.md", show_error=False))
        self.assertEqual(window.outline._items, old_items)
        window._display_document(Path("second.md"), "## Second")
        self.assertEqual([item.text(0) for item in window.outline._items], ["Second"])

    def test_h3_stops_at_same_or_higher_heading(self) -> None:
        window = self.window("## A\n### One\n1\n### Two\n2\n## B\n3")
        self.assertNotIn("Two", self.selected(window, 1))
        self.assertNotIn("B", self.selected(window, 2))

    def test_final_empty_and_consecutive_sections(self) -> None:
        window = self.window("## Empty\n## Final\nlast")
        self.assertEqual(self.selected(window, 0).strip(), "Empty")
        self.assertIn("last", self.selected(window, 1))

    def test_rich_section_selects_complete_rendered_content(self) -> None:
        source = "## Rich\n- list\n\n> quote\n\n| A | B |\n|---|---|\n| x | y |\n\n![alt](x.png)\n\n```py\nprint(1)\n```\n## End"
        selected = self.selected(self.window(source), 0)
        for text in ("Rich", "list", "quote", "A", "B", "x", "y", "print(1)"):
            self.assertIn(text, selected)
        self.assertNotIn("End", selected)

    def test_selection_enables_copy_and_does_not_copy_automatically(self) -> None:
        window = self.window("## A\nbody\n## B")
        self.app.processEvents()
        clipboard = QApplication.clipboard()
        clipboard.clear()
        spy = QSignalSpy(clipboard.dataChanged)
        window.select_section(window.viewer.regions.headings[0])
        self.assertTrue(window.copy_plain_action.isEnabled())
        self.assertTrue(window.copy_html_action.isEnabled())
        self.assertEqual(spy.count(), 0)
        self.app.processEvents()
        window.copy_as_plain_text()
        self.assertIn("body", QApplication.clipboard().text())
        self.app.processEvents()
        window.copy_as_html()
        self.assertIn("<h2>A</h2>", QApplication.clipboard().text())

    def test_code_copy_uses_source_and_plain_text_only(self) -> None:
        source = "```python\nif a < b and č:\n\tprint(\"&\")\n```\nprose\n```\nsame\n```"
        window = self.window(source)
        self.assertEqual(len(window.viewer.regions.code_blocks), 2)
        self.app.processEvents()
        window.copy_code_region(window.viewer.regions.code_blocks[0])
        mime = QApplication.clipboard().mimeData()
        self.assertEqual(mime.formats(), ["text/plain"])
        self.assertEqual(mime.text(), "if a < b and č:\n\tprint(\"&\")\n")
        self.assertNotIn("prose", mime.text())

    def test_empty_fence_does_not_shift_later_rendered_mapping(self) -> None:
        window = self.window("```\n```\n```text\nlater\n```")
        self.assertEqual(len(window.viewer.regions.code_blocks), 1)
        self.assertEqual(window.viewer.regions.code_blocks[0].code, "later\n")

    def test_keyboard_actions_track_cursor_regions(self) -> None:
        window = self.window("## A\nbody\n```\ncode\n```\n## B")
        cursor = window.viewer.document().find("body")
        window.viewer.setTextCursor(cursor)
        self.assertTrue(window.select_section_action.isEnabled())
        self.assertFalse(window.copy_code_action.isEnabled())
        cursor = window.viewer.document().find("code")
        window.viewer.setTextCursor(cursor)
        self.assertTrue(window.copy_code_action.isEnabled())
        self.app.processEvents()
        window.copy_current_code_block()
        self.assertEqual(QApplication.clipboard().text(), "code\n")

    def test_metadata_rebuild_and_failed_open_preservation(self) -> None:
        window = self.window("# First\n```\none\n```")
        old = window.viewer.regions
        second = Path("tests/fixtures/regions-second.md")
        second.write_text("## Second\ntext", encoding="utf-8")
        try:
            self.assertTrue(window.open_file(second))
            self.assertEqual(len(window.viewer.regions.headings), 1)
            self.assertEqual(len(window.viewer.regions.code_blocks), 0)
            current = window.viewer.regions
            self.assertFalse(window.open_file("tests/fixtures/missing.md", show_error=False))
            self.assertIs(window.viewer.regions, current)
            self.assertIsNot(window.viewer.regions, old)
        finally:
            second.unlink(missing_ok=True)

    def test_no_regions_behaves_normally_and_controls_are_not_document_content(self) -> None:
        window = self.window("plain text")
        self.assertEqual(window.viewer.regions.headings, ())
        self.assertEqual(window.viewer.regions.code_blocks, ())
        window.viewer.selectAll()
        self.assertNotIn("Select section", window.viewer.toPlainText())
        self.assertNotIn("Copy code", window.viewer.toHtml())

    def test_overlay_positions_follow_scroll_and_resize(self) -> None:
        source = "# Heading\n\n```\ncode\n```\n\n" + "\n\n".join(f"line {n}" for n in range(80))
        window = self.window(source)
        window.resize(520, 260)
        window.show()
        self.app.processEvents()
        viewer = window.viewer
        viewer._hovered_heading = viewer.regions.headings[0]
        viewer._hovered_code = viewer.regions.code_blocks[0]
        viewer._position_overlays()
        self.assertTrue(viewer._section_button.isVisible())
        self.assertTrue(viewer._code_button.isVisible())
        heading_before = viewer._section_button.pos()
        code_before = viewer._code_button.pos()
        viewer.verticalScrollBar().setValue(20)
        self.app.processEvents()
        self.assertLess(viewer._section_button.y(), heading_before.y())
        self.assertLess(viewer._code_button.y(), code_before.y())
        window.resize(760, 260)
        self.app.processEvents()
        self.assertLessEqual(viewer._code_button.x(), viewer.viewport().width() - 28)


if __name__ == "__main__":
    unittest.main()
