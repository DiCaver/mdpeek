from __future__ import annotations

import unittest
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

from mdpeek.app import MarkdownWindow
from mdpeek.markdown_copy import selected_markdown


class MarkdownCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def window(self, source: str) -> MarkdownWindow:
        return MarkdownWindow(Path("copy.md"), source)

    def test_full_selection_is_exact_and_action_has_shortcut(self) -> None:
        source = "---\ntitle: Exact\n---\r\n\r\n# Title\r\n<!-- tail -->\r\n"
        window = self.window(source)
        window.viewer.selectAll()
        self.assertEqual(selected_markdown(window.viewer.textCursor(), source, window.viewer.regions), source)
        self.assertEqual(window.copy_markdown_action.shortcut().toString(), "Ctrl+Shift+M")

    def test_repeated_text_uses_rendered_position_and_format(self) -> None:
        window = self.window("**same**\n\n*same*\n\n[same](https://example.com)\n\n`same`")
        outputs = []
        block = window.viewer.document().begin()
        while block.isValid():
            cursor = window.viewer.document().find("same", block.position())
            if cursor.hasSelection() and cursor.block() == block:
                outputs.append(selected_markdown(cursor, window.source_markdown, window.viewer.regions))
            block = block.next()
        self.assertEqual(outputs, ["**same**", "*same*", "[same](https://example.com)", "`same`"])

    def test_partial_strong_and_link_are_balanced(self) -> None:
        window = self.window("Before **very important text** and [OpenAI](https://openai.com).")
        strong = window.viewer.document().find("important")
        self.assertEqual(selected_markdown(strong, window.source_markdown, window.viewer.regions), "**important**")
        link = window.viewer.document().find("Open")
        self.assertEqual(selected_markdown(link, window.source_markdown, window.viewer.regions), "[Open](https://openai.com)")

    def test_clipboard_plain_and_markdown_mime_without_html(self) -> None:
        window = self.window("## Heading\n\nBody")
        window.viewer.selectAll(); window.copy_as_markdown()
        mime = QApplication.clipboard().mimeData()
        self.assertEqual(mime.text(), window.source_markdown)
        self.assertEqual(mime.data("text/markdown"), QByteArray(window.source_markdown.encode()))
        self.assertFalse(mime.hasHtml())

    def test_welcome_and_empty_selection_are_disabled(self) -> None:
        welcome = MarkdownWindow()
        welcome.viewer.selectAll()
        self.assertFalse(welcome.copy_markdown_action.isEnabled())
        window = self.window("text")
        self.assertFalse(window.copy_markdown_action.isEnabled())


if __name__ == "__main__":
    unittest.main()
