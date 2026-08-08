import os
import sys
import unittest
from pathlib import Path

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import (
    QFont,
    QKeySequence,
    QPalette,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextFrameFormat,
    QTextTable,
    QTextTableCellFormat,
)
from PySide6.QtWidgets import QApplication, QTextBrowser

from mdpeek.app import EMPTY_MESSAGE, MarkdownWindow, build_parser, read_markdown
from mdpeek.clipboard import markdown_for_complete_selection, plain_mime_data, selected_clean_html
from mdpeek.highlight import find_code_fences, lexer_for_language
from mdpeek.style import (
    CODE_PANEL,
    LARGE_WINDOW_GUTTER,
    PANEL_KIND_PROPERTY,
    QUOTE_PANEL,
    SMALL_WINDOW_GUTTER,
    code_font_family,
    document_stylesheet,
    reading_font_family,
    window_gutter,
)


def _fragments(block):  # type: ignore[no-untyped-def]
    iterator = block.begin()
    while not iterator.atEnd():
        yield iterator.fragment()
        iterator += 1


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
        self.assertIn("Ctrl+O", viewer.toPlainText())
        self.assertIn("drag and drop", viewer.toPlainText())
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

    def test_opening_second_file_updates_document_title_base_and_scroll(self) -> None:
        first = Path("README.md")
        second = Path("examples/showcase.md")
        window = MarkdownWindow()
        self.assertTrue(window.open_file(first))
        window.viewer.verticalScrollBar().setValue(10)
        self.assertTrue(window.open_file(second))
        self.assertIn("MDPeek Markdown Showcase", window.viewer.toPlainText())
        self.assertEqual(window.windowTitle(), "showcase.md — MDPeek")
        self.assertEqual(window.current_path, second.resolve())
        self.assertEqual(
            window.viewer.document().baseUrl(),
            QUrl.fromLocalFile(str(second.parent.resolve()) + "/"),
        )
        self.assertEqual(
            window.viewer.document().baseUrl().resolved(QUrl("mdpeek-mark.svg")),
            QUrl.fromLocalFile(str((second.parent / "mdpeek-mark.svg").resolve())),
        )
        self.assertEqual(window.viewer.verticalScrollBar().value(), 0)

    def test_failed_open_preserves_current_document_and_path(self) -> None:
        path = Path("README.md")
        window = MarkdownWindow()
        self.assertTrue(window.open_file(path))
        title = window.windowTitle()
        self.assertFalse(window.open_file(Path("missing.md"), show_error=False))
        self.assertEqual(window.current_path, path.resolve())
        self.assertEqual(window.windowTitle(), title)
        self.assertIn("MDPeek", window.viewer.toPlainText())

    def test_drop_validation_accepts_only_one_local_markdown_file(self) -> None:
        markdown = Path("tests/fixtures/drop.MARKDOWN").resolve()
        unsupported = Path("pyproject.toml").resolve()

        def mime(*urls: QUrl) -> QMimeData:
            data = QMimeData()
            data.setUrls(list(urls))
            return data

        local = QUrl.fromLocalFile(str(markdown))
        self.assertEqual(MarkdownWindow.dropped_markdown_path(mime(local)), markdown)
        self.assertIsNone(MarkdownWindow.dropped_markdown_path(
            mime(QUrl.fromLocalFile(str(Path.cwd())))
        ))
        self.assertIsNone(MarkdownWindow.dropped_markdown_path(
            mime(QUrl("https://example.com/readme.md"))
        ))
        self.assertIsNone(MarkdownWindow.dropped_markdown_path(
            mime(QUrl.fromLocalFile(str(unsupported)))
        ))
        self.assertIsNone(MarkdownWindow.dropped_markdown_path(mime(local, local)))

    def test_open_action_has_standard_shortcut(self) -> None:
        window = MarkdownWindow()
        self.assertEqual(window.open_action.shortcut().toString(), "Ctrl+O")

    def test_clipboard_actions_follow_selection(self) -> None:
        window = MarkdownWindow(Path("example.md"), "Visible text")
        self.assertFalse(window.copy_plain_action.isEnabled())
        self.assertFalse(window.copy_html_action.isEnabled())
        self.assertTrue(window.select_all_action.isEnabled())
        window.viewer.selectAll()
        self.assertTrue(window.copy_plain_action.isEnabled())
        self.assertTrue(window.copy_html_action.isEnabled())
        self.assertEqual(window.copy_plain_action.shortcut(), QKeySequence.StandardKey.Copy)
        self.assertEqual(window.select_all_action.shortcut(), QKeySequence.StandardKey.SelectAll)
        self.assertEqual(window.copy_html_action.shortcut().toString(), "Ctrl+Shift+C")

    def test_plain_copy_is_visible_selected_text_with_native_newlines(self) -> None:
        markdown = "# Heading\n\nText with **bold**, č, š, and ž.\n\n```\na < b && c > d\n```"
        window = MarkdownWindow(Path("example.md"), markdown)
        window.viewer.selectAll()
        text = plain_mime_data(window.viewer.textCursor()).text()
        self.assertIn("Heading", text)
        self.assertIn("Text with bold, č, š, and ž.", text)
        self.assertIn("a < b && c > d", text)
        self.assertNotIn("**", text)
        self.assertNotIn("\u2029", text)
        cursor = window.viewer.document().find("bold")
        window.viewer.setTextCursor(cursor)
        self.assertEqual(plain_mime_data(window.viewer.textCursor()).text(), "bold")

    def test_html_copy_is_clean_semantic_source_in_plain_text(self) -> None:
        markdown = "# Heading\n\nThis is **important** and *soft* with [link](guide.md).\n\n- one\n- two\n\n> A **quote**.\n\n`inline`\n\n```html\n<a>& value\n```\n\n| A | B |\n|---|---|\n| x | y |\n\n---\n\n![Alt](img/picture.png)"
        window = MarkdownWindow(Path("example.md"), markdown)
        window.viewer.selectAll()
        window.copy_as_html()
        mime = QApplication.clipboard().mimeData()
        html = mime.text()
        self.assertEqual(mime.html(), html)
        for expected in ("<h1>Heading</h1>", "<p>This is", "<strong>important</strong>", "<em>soft</em>", '<a href="guide.md">link</a>', "<ul>\n    <li>one</li>", "<blockquote>", "<strong>quote</strong>", "<code>inline</code>", "<pre><code>&lt;a&gt;&amp; value</code></pre>", "<table>\n    <tr>", "<th>", "<hr>", '<img src="img/picture.png" alt="Alt">'):
            self.assertIn(expected, html)
        for forbidden in ("<html", "<head", "<body", "<style", "style=", "class=", "qrichtext", "color:", "<span"):
            self.assertNotIn(forbidden, html.lower())

    def test_html_copy_pretty_prints_nested_lists(self) -> None:
        markdown = "- An unordered item\n- Another item with nested content\n  - A nested item\n  - A second nested item"
        window = MarkdownWindow(Path("example.md"), markdown)
        window.viewer.selectAll()
        self.assertEqual(
            selected_clean_html(window.viewer.textCursor()),
            "<ul>\n"
            "    <li>An unordered item</li>\n"
            "    <li>Another item with nested content\n"
            "        <ul>\n"
            "            <li>A nested item</li>\n"
            "            <li>A second nested item</li>\n"
            "        </ul>\n"
            "    </li>\n"
            "</ul>",
        )

    def test_html_copy_excludes_unselected_content(self) -> None:
        window = MarkdownWindow(Path("example.md"), "Before **chosen** after")
        cursor = window.viewer.document().find("chosen")
        window.viewer.setTextCursor(cursor)
        html = selected_clean_html(cursor)
        self.assertIn("chosen", html)
        self.assertNotIn("Before", html)
        self.assertNotIn("after", html)

    def test_source_markdown_lifecycle_and_complete_selection_helper(self) -> None:
        first_source = "# Exact\n\n**source**\n"
        window = MarkdownWindow(Path("first.md"), first_source)
        self.assertEqual(window.source_markdown, first_source)
        window.viewer.selectAll()
        self.assertEqual(markdown_for_complete_selection(window.viewer.textCursor(), window.source_markdown), first_source)
        second = Path("tests/fixtures/drop.MARKDOWN")
        second_source = read_markdown(second)
        self.assertTrue(window.open_file(second))
        self.assertEqual(window.source_markdown, second_source)
        rendered = window.viewer.toPlainText()
        self.assertFalse(window.open_file(Path("tests/fixtures/missing.md"), show_error=False))
        self.assertEqual(window.source_markdown, second_source)
        self.assertEqual(window.viewer.toPlainText(), rendered)

    def test_context_menu_has_only_read_only_document_commands(self) -> None:
        window = MarkdownWindow(Path("example.md"), "Some text")
        menu = window._context_menu(QPoint(0, 0))
        labels = [action.text().replace("&", "") for action in menu.actions() if not action.isSeparator()]
        self.assertEqual(labels, [
            "Copy as Plain Text", "Copy as HTML", "Select Current Section",
            "Copy Current Code Block", "Select All",
        ])
        for editing in ("Cut", "Paste", "Delete", "Undo"):
            self.assertNotIn(editing, labels)

    def test_remote_images_are_requested_asynchronously(self) -> None:
        url = QUrl("https://example.com/picture.png")
        window = MarkdownWindow(Path("example.md"), f"![remote]({url.toString()})")
        viewer = window.centralWidget()
        result = viewer.loadResource(QTextDocument.ResourceType.ImageResource, url)
        self.assertIsInstance(result, QByteArray)
        self.assertIn(url, viewer._pending_images)

    def test_style_configuration_covers_document_elements(self) -> None:
        css = document_stylesheet()
        for selector in ("body", "p", "h1", "h6", "ul, ol", "blockquote", "a", "code", "pre", "hr", "table", "th", "td"):
            self.assertIn(f"{selector} {{", css)
        self.assertTrue(reading_font_family())
        self.assertTrue(code_font_family())
        self.assertIn('li.checked::marker { content: "\\2611"; }', css)

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
        code_frames = [
            frame for frame in document.rootFrame().childFrames()
            if frame.format().property(PANEL_KIND_PROPERTY) == CODE_PANEL
        ]
        self.assertEqual(len(code_frames), 1)

    def test_inline_code_background_includes_surrounding_spaces(self) -> None:
        window = MarkdownWindow(Path("example.md"), "Before `code` after")
        document = window.centralWidget().document()
        code = document.find("code")
        start = code.selectionStart()
        end = code.selectionEnd()
        for position in (start - 1, end):
            cursor = QTextCursor(document)
            cursor.setPosition(position)
            cursor.setPosition(position + 1, QTextCursor.MoveMode.KeepAnchor)
            self.assertNotEqual(
                cursor.charFormat().background().style(), Qt.BrushStyle.NoBrush
            )
        for position in (start - 2, end + 1):
            cursor = QTextCursor(document)
            cursor.setPosition(position)
            cursor.setPosition(position + 1, QTextCursor.MoveMode.KeepAnchor)
            self.assertEqual(
                cursor.charFormat().background().style(), Qt.BrushStyle.NoBrush
            )

    def test_table_headers_are_bold_and_vertically_centered(self) -> None:
        markdown = "| Feature | Example |\n| --- | --- |\n| Code | `inline` |"
        window = MarkdownWindow(Path("example.md"), markdown)
        document = window.centralWidget().document()
        table = next(
            frame for frame in document.rootFrame().childFrames()
            if isinstance(frame, QTextTable)
        )
        self.assertEqual(table.format().margin(), 8)
        for column in range(table.columns()):
            cell = table.cellAt(0, column)
            self.assertEqual(
                QTextTableCellFormat(cell.format()).verticalAlignment(),
                QTextCharFormat.VerticalAlignment.AlignMiddle,
            )
            block = document.find(["Feature", "Example"][column]).block()
            self.assertGreaterEqual(
                block.begin().fragment().charFormat().fontWeight(),
                QFont.Weight.DemiBold,
            )
            self.assertEqual(block.blockFormat().topMargin(), 0)
            self.assertEqual(block.blockFormat().bottomMargin(), 0)

    def test_fence_scanner_preserves_code_and_languages(self) -> None:
        markdown = "```py\nprint('č')\n\n# comment\n```\n~~~mystery\na < b & c\n~~~"
        fences = find_code_fences(markdown)
        self.assertEqual(fences[0].language, "py")
        self.assertEqual(fences[0].lines, ("print('č')", "", "# comment"))
        self.assertEqual(fences[1].language, "mystery")
        self.assertEqual(fences[1].lines, ("a < b & c",))

    def test_supported_languages_and_aliases_have_lexers(self) -> None:
        for language in (
            "python", "javascript", "typescript", "css", "html", "csharp",
            "sql", "json", "powershell", "bash", "js", "ts", "cs", "py", "ps1", "sh",
        ):
            with self.subTest(language=language):
                self.assertIsNotNone(lexer_for_language(language))
        self.assertIsNone(lexer_for_language(None))
        self.assertIsNone(lexer_for_language("not-a-real-language"))

    def test_highlighting_preserves_plain_text_and_falls_back_safely(self) -> None:
        markdown = "```py\nvalue = 'č'\n```\n\n```mystery\nx < y & z\n```\n\n```\nplain & exact\n```"
        window = MarkdownWindow(Path("example.md"), markdown)
        document = window.centralWidget().document()
        content_lines = [line for line in document.toPlainText().splitlines() if line]
        self.assertEqual(content_lines, ["value = 'č'", "x < y & z", "plain & exact"])
        python_block = document.find("value =").block()
        python_colors = {
            fragment.charFormat().foreground().color().name()
            for fragment in _fragments(python_block)
        }
        unknown_block = document.find("x < y").block()
        plain_block = document.find("plain & exact").block()
        self.assertGreater(len(python_colors), 1)
        self.assertEqual(len({f.charFormat().foreground().color().name() for f in _fragments(unknown_block)}), 1)
        self.assertEqual(len({f.charFormat().foreground().color().name() for f in _fragments(plain_block)}), 1)
        self.assertTrue(any(
            frame.format().property(PANEL_KIND_PROPERTY) == CODE_PANEL
            for frame in document.rootFrame().childFrames()
        ))

    def test_fenced_lines_form_one_visual_panel(self) -> None:
        window = MarkdownWindow(Path("example.md"), "```python\none = 1\ntwo = 2\n```")
        document = window.centralWidget().document()
        frames = document.rootFrame().childFrames()
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].format().property(PANEL_KIND_PROPERTY), CODE_PANEL)
        frame_format = QTextFrameFormat(frames[0].format())
        self.assertEqual(frame_format.padding(), 12)
        self.assertEqual(frame_format.margin(), 8)

    def test_multi_paragraph_quote_forms_one_visual_panel(self) -> None:
        markdown = "> First paragraph.\n>\n> Second paragraph."
        window = MarkdownWindow(Path("example.md"), markdown)
        document = window.centralWidget().document()
        frames = document.rootFrame().childFrames()
        quote_frames = [
            frame for frame in frames
            if frame.format().property(PANEL_KIND_PROPERTY) == QUOTE_PANEL
        ]
        self.assertEqual(len(quote_frames), 1)
        self.assertEqual(QTextFrameFormat(quote_frames[0].format()).padding(), 10)
        first_quote_block = document.find("First paragraph.").block()
        self.assertEqual(first_quote_block.blockFormat().bottomMargin(), 10)

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
