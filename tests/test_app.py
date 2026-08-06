import os
import sys
import unittest
from pathlib import Path

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPalette, QTextFormat
from PySide6.QtWidgets import QApplication, QTextBrowser

from mdpeek.app import EMPTY_MESSAGE, MarkdownWindow, build_parser, read_markdown
from mdpeek.style import (
    LARGE_WINDOW_GUTTER,
    SMALL_WINDOW_GUTTER,
    code_font_family,
    document_stylesheet,
    reading_font_family,
    window_gutter,
)


class MDPeekTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_optional_file_argument(self) -> None:
        self.assertIsNone(build_parser().parse_args([]).file)
        self.assertEqual(build_parser().parse_args(["notes.md"]).file, Path("notes.md"))

    def test_reads_markdown(self) -> None:
        self.assertTrue(read_markdown(Path("README.md")).startswith("# MDPeek"))

    def test_rejects_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            read_markdown(Path("does-not-exist.md"))

    def test_empty_window_is_helpful_and_read_only(self) -> None:
        window = MarkdownWindow()
        viewer = window.centralWidget()
        self.assertIsInstance(viewer, QTextBrowser)
        self.assertTrue(viewer.isReadOnly())
        self.assertGreaterEqual(viewer.font().pointSize(), 11)
        self.assertIn("MDPeek", viewer.toPlainText())
        self.assertIn("mdpeek README.md", viewer.toPlainText())
        self.assertIn("MDPeek", EMPTY_MESSAGE)

    def test_file_window_renders_markdown(self) -> None:
        path = Path.cwd() / "sample.md"
        window = MarkdownWindow(path, "# Heading\n\nSome **bold** text.")
        viewer = window.centralWidget()
        self.assertEqual(window.windowTitle(), "sample.md — MDPeek")
        self.assertIn("Heading", viewer.toPlainText())
        self.assertIn("Some bold text.", viewer.toPlainText())

    def test_viewer_preserves_read_only_interactions(self) -> None:
        window = MarkdownWindow()
        viewer = window.centralWidget()
        flags = viewer.textInteractionFlags()
        self.assertTrue(viewer.isReadOnly())
        self.assertTrue(viewer.openExternalLinks())
        self.assertTrue(flags & Qt.TextInteractionFlag.TextSelectableByMouse)
        self.assertTrue(flags & Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.assertTrue(flags & Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.assertEqual(
            viewer.palette().color(QPalette.ColorRole.Base),
            window.palette().color(QPalette.ColorRole.Window),
        )

    def test_relative_resources_use_markdown_directory(self) -> None:
        path = (Path.cwd() / "examples" / "showcase.md").resolve()
        window = MarkdownWindow(path, read_markdown(path))
        viewer = window.centralWidget()
        expected = QUrl.fromLocalFile(str(path.parent) + "/")
        self.assertEqual(viewer.document().baseUrl(), expected)
        self.assertIn("mdpeek-mark.svg", viewer.document().toHtml())

    def test_style_configuration_covers_document_elements(self) -> None:
        css = document_stylesheet()
        for selector in ("body", "p", "h1", "h6", "ul, ol", "blockquote", "a", "code", "pre", "hr", "table", "th", "td"):
            self.assertIn(f"{selector} {{", css)
        self.assertTrue(reading_font_family())
        self.assertTrue(code_font_family())

    def test_parsed_document_receives_reading_formats(self) -> None:
        window = MarkdownWindow(Path("example.md"), "# Heading\n\n`inline`\n\n```py\ncode\n```")
        document = window.centralWidget().document()
        heading = document.begin()
        self.assertEqual(heading.blockFormat().headingLevel(), 1)
        self.assertEqual(heading.begin().fragment().charFormat().fontPointSize(), 24)
        inline = heading.next()
        self.assertNotEqual(inline.begin().fragment().charFormat().background().style(), Qt.BrushStyle.NoBrush)
        fenced = inline.next()
        self.assertTrue(fenced.blockFormat().property(QTextFormat.Property.BlockNonBreakableLines))
        self.assertNotEqual(fenced.blockFormat().background().style(), Qt.BrushStyle.NoBrush)

    def test_window_gutter_is_responsive(self) -> None:
        self.assertEqual(window_gutter(900), LARGE_WINDOW_GUTTER)
        self.assertEqual(window_gutter(500), SMALL_WINDOW_GUTTER)
        window = MarkdownWindow()
        window.resize(500, 600)
        window.show()
        self.app.processEvents()
        self.assertEqual(window.centralWidget().viewportMargins().left(), SMALL_WINDOW_GUTTER)


if __name__ == "__main__":
    unittest.main()
