import os
import sys
import unittest
from pathlib import Path

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication

from mdpeek.app import HELP_MARKDOWN, MarkdownWindow, initial_window_geometry
from mdpeek.content import safe_markdown
from mdpeek.printing import suggested_pdf_path


class Phase9Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_outline_starts_hidden_and_remains_user_controlled(self) -> None:
        for window in (MarkdownWindow(), MarkdownWindow(Path("sample.md"), "# Heading")):
            window.show()
            self.app.processEvents()
            self.assertFalse(window.outline.isVisible())
            self.assertEqual(window.outline.windowTitle(), "Outline")
            window.outline_action.trigger()
            self.app.processEvents()
            self.assertTrue(window.outline.isVisible())
            window._display_document(Path("next.md"), "# Next")
            self.assertTrue(window.outline.isVisible())

    def test_portrait_geometry_fits_small_work_area(self) -> None:
        geometry = initial_window_geometry(QRect(20, 30, 640, 700))
        self.assertEqual(geometry, QRect(20, 30, 640, 700))
        self.assertGreater(geometry.height(), geometry.width())

    def test_help_and_caret_configuration(self) -> None:
        window = MarkdownWindow(Path("sample.md"), "content")
        self.assertEqual(window.help_action.shortcut().toString(), "F1")
        self.assertEqual(window.viewer.cursorWidth(), 0)
        for shortcut in ("Ctrl+O", "Ctrl+A", "Ctrl+C", "Ctrl+Shift+M", "Ctrl+Shift+C", "Ctrl+F", "Alt+Left", "Alt+Right", "Ctrl+H", "Ctrl+P"):
            self.assertIn(shortcut, HELP_MARKDOWN)
        self.assertEqual(window.current_path, Path("sample.md").resolve())

    def test_icons_are_real_and_revealed_state_has_labels(self) -> None:
        window = MarkdownWindow(Path("sample.md"), "# Heading\n\n```\ncode\n```")
        self.assertFalse(window.viewer._section_button.icon().isNull())
        self.assertFalse(window.viewer._code_button.icon().isNull())
        self.assertEqual(window.viewer._section_button.toolTip(), "Select this section")
        self.assertEqual(window.viewer._code_button.toolTip(), "Copy code")

    def test_pdf_names(self) -> None:
        self.assertEqual(suggested_pdf_path(Path("README.md")), Path("README.pdf"))
        self.assertEqual(suggested_pdf_path(Path("Guide.markdown")), Path("Guide.pdf"))
        self.assertEqual(suggested_pdf_path(Path("notes.txt")), Path("notes.pdf"))
        self.assertEqual(suggested_pdf_path(None), Path("MDPeek.pdf"))

    def test_raw_html_is_safe_and_following_markdown_survives(self) -> None:
        source = '<p align="center">\n<img src="assets/icon.svg" alt="Icon" onclick="bad()">\n</p>\n# After\n\n- item\n\n<script>alert(1)</script>\nParagraph with <kbd>Ctrl</kbd><br>next'
        prepared = safe_markdown(source)
        self.assertIn("![Icon](assets/icon.svg)", prepared)
        self.assertIn("# After", prepared)
        self.assertIn("- item", prepared)
        self.assertIn("`Ctrl`", prepared)
        self.assertNotIn("script", prepared.lower())
        self.assertNotIn("onclick", prepared.lower())
        window = MarkdownWindow(Path("sample.md"), source)
        self.assertIn("After", window.viewer.toPlainText())
        self.assertIn("item", window.viewer.toPlainText())

    def test_refresh_preserves_history_and_last_good_content(self) -> None:
        path = Path("tests/fixtures/_phase9_live.md")
        try:
            path.write_text("# Old", encoding="utf-8")
            window = MarkdownWindow()
            window.open_file(path)
            count = len(window.history.entries)
            path.write_text("# New", encoding="utf-8")
            window._reload_watched_file()
            self.assertIn("New", window.viewer.toPlainText())
            self.assertEqual(len(window.history.entries), count)
            path.unlink()
            window._refresh_attempts = 5
            window._reload_watched_file()
            self.assertIn("New", window.viewer.toPlainText())
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
