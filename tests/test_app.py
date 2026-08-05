import os
import sys
import unittest
from pathlib import Path

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTextBrowser

from mdpeek.app import EMPTY_MESSAGE, MarkdownWindow, build_parser, read_markdown


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


if __name__ == "__main__":
    unittest.main()
