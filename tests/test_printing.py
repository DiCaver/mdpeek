import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QImage, QTextCursor, QTextDocument, QTextFormat, QTextImageFormat
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from mdpeek.app import MarkdownWindow
from mdpeek.printing import create_printer, prepare_printable_document


class PrintingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_print_action_lifecycle_and_shortcut_scope(self) -> None:
        window = MarkdownWindow()
        self.assertFalse(window.print_action.isEnabled())
        self.assertEqual(window.print_action.shortcut().toString(), "Ctrl+P")
        self.assertEqual(window.print_action.shortcutContext(), Qt.ShortcutContext.WindowShortcut)
        self.assertFalse(window.open_file("missing.md", show_error=False))
        self.assertFalse(window.print_action.isEnabled())

        self.assertTrue(window.open_file("README.md"))
        self.assertTrue(window.print_action.isEnabled())
        self.assertFalse(window.open_file("missing.md", show_error=False))
        self.assertTrue(window.print_action.isEnabled())

        window.show()
        self.app.processEvents()
        with patch("mdpeek.app.open_print_preview", return_value=0) as preview:
            window.viewer.setFocus()
            QTest.keyClick(window.viewer, Qt.Key.Key_P, Qt.KeyboardModifier.ControlModifier)
            self.app.processEvents()
            window.outline.tree.setFocus()
            QTest.keyClick(window.outline.tree, Qt.Key.Key_P, Qt.KeyboardModifier.ControlModifier)
            self.app.processEvents()
            self.assertEqual(preview.call_count, 2)

    def test_supplied_document_enables_print_and_welcome_does_not_preview(self) -> None:
        welcome = MarkdownWindow()
        loaded = MarkdownWindow(Path("sample.md"), "# Loaded")
        self.assertFalse(welcome.print_action.isEnabled())
        self.assertTrue(loaded.print_action.isEnabled())
        with patch("mdpeek.app.open_print_preview") as preview:
            welcome.show_print_preview()
            preview.assert_not_called()

    def test_printable_document_is_independent_complete_and_paper_styled(self) -> None:
        markdown = (
            "# Heading č š ž\n\nParagraph with **strong**, *emphasis*, "
            "[a link](https://example.com), and `inline`.\n\n"
            "- item\n- [x] task\n\n> quote\n\n"
            "```python\nvalue = 1\n```\n\n"
            "| A | B |\n|---|---|\n| x | y |\n\n---\n"
        )
        window = MarkdownWindow(Path("sample.md"), markdown)
        selection = window.viewer.document().find("strong")
        window.viewer.setTextCursor(selection)
        live_html = window.viewer.document().toHtml()
        live_text = window.viewer.document().toPlainText()

        printable = prepare_printable_document(
            window.viewer.document(), window.source_markdown, create_printer()
        )

        self.assertIsNot(printable, window.viewer.document())
        self.assertEqual(window.viewer.document().toHtml(), live_html)
        self.assertEqual(window.viewer.document().toPlainText(), live_text)
        for text in ("Heading č š ž", "Paragraph", "item", "task", "quote", "value = 1", "A", "y"):
            self.assertIn(text, printable.toPlainText())
        heading = printable.begin()
        self.assertEqual(heading.blockFormat().headingLevel(), 1)
        link = printable.find("a link")
        self.assertTrue(link.charFormat().isAnchor())
        self.assertTrue(link.charFormat().fontUnderline())
        self.assertLess(link.charFormat().foreground().color().lightness(), 150)
        self.assertEqual(
            printable.rootFrame().frameFormat().background().color(), QColor("#ffffff")
        )
        self.assertFalse(printable.find("strong").charFormat().background().color() == window.palette().highlight().color())

    def test_available_image_is_retained_and_oversized_image_is_scaled(self) -> None:
        window = MarkdownWindow(Path("sample.md"), "![picture](large.png)")
        image = QImage(2400, 1200, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.red)
        url = QUrl("large.png")
        resolved_url = window.viewer.document().baseUrl().resolved(url)
        window.viewer.document().addResource(
            QTextDocument.ResourceType.ImageResource, resolved_url, image
        )
        printable = prepare_printable_document(
            window.viewer.document(), window.source_markdown, create_printer()
        )
        resource = printable.resource(QTextDocument.ResourceType.ImageResource, resolved_url)
        self.assertFalse(resource.isNull())
        iterator = printable.begin().begin()
        image_format = QTextImageFormat()
        while not iterator.atEnd():
            candidate = QTextImageFormat(iterator.fragment().charFormat())
            if candidate.isValid():
                image_format = candidate
                break
            iterator += 1
        self.assertTrue(image_format.isValid())
        self.assertLessEqual(image_format.width(), printable.pageSize().width())
        self.assertAlmostEqual(image_format.width() / image_format.height(), 2.0, places=2)

    def test_long_document_paginates_and_code_wraps(self) -> None:
        markdown = "# Long\n\n" + "\n\n".join(f"Paragraph {i} " + "word " * 40 for i in range(180))
        markdown += "\n\n```text\n" + "x" * 2000 + "\n```\n\nFINAL MARKER"
        window = MarkdownWindow(Path("long.md"), markdown)
        printable = prepare_printable_document(
            window.viewer.document(), window.source_markdown, create_printer()
        )
        self.assertGreater(printable.pageCount(), 1)
        self.assertTrue(printable.toPlainText().rstrip().endswith("FINAL MARKER"))
        code = printable.find("x" * 20).block()
        self.assertFalse(code.blockFormat().property(QTextFormat.Property.BlockNonBreakableLines))

    def test_preview_route_preserves_window_state_and_uses_current_history_item(self) -> None:
        window = MarkdownWindow()
        window.open_file("README.md")
        window.open_file("examples/showcase.md")
        window.go_back()
        cursor = window.viewer.document().find("MDPeek")
        window.viewer.setTextCursor(cursor)
        before = (
            window.current_path,
            window.source_markdown,
            window.viewer.document().toHtml(),
            window.viewer.verticalScrollBar().value(),
            window.viewer.textCursor().selectionStart(),
            window.viewer.textCursor().selectionEnd(),
            list(window.history.entries),
            window.history.current_index,
        )
        with patch("mdpeek.app.open_print_preview", return_value=0) as preview:
            window.show_print_preview()
            factory = preview.call_args.args[2]
            printable = factory(create_printer())
        self.assertIn("MDPeek", printable.toPlainText())
        self.assertEqual(before, (
            window.current_path,
            window.source_markdown,
            window.viewer.document().toHtml(),
            window.viewer.verticalScrollBar().value(),
            window.viewer.textCursor().selectionStart(),
            window.viewer.textCursor().selectionEnd(),
            list(window.history.entries),
            window.history.current_index,
        ))


if __name__ == "__main__":
    unittest.main()
