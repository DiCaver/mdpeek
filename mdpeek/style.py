"""Presentation settings for MDPeek's Qt text document."""

from __future__ import annotations

from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPalette,
    QTextBlockFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextFrame,
    QTextTable,
)

from .highlight import apply_syntax_highlighting, find_code_fences

LARGE_WINDOW_GUTTER = 18
SMALL_WINDOW_GUTTER = 8
GUTTER_BREAKPOINT = 640


def first_available_font(candidates: tuple[str, ...]) -> str:
    installed = set(QFontDatabase.families())
    for family in candidates:
        if family in installed:
            return family
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()


def reading_font_family() -> str:
    return first_available_font(("Segoe UI Variable Text", "Segoe UI"))


def code_font_family() -> str:
    return first_available_font(
        ("Cascadia Mono", "Cascadia Code", "Consolas", "Courier New")
    )


def document_font() -> QFont:
    font = QFont(reading_font_family(), 11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def document_stylesheet() -> str:
    """Return CSS supported by QTextDocument's rich-text renderer."""
    body = reading_font_family().replace('"', "")
    code = code_font_family().replace('"', "")
    return f"""
body {{ color: #24292f; font-family: \"{body}\"; font-size: 11pt; }}
p {{ margin-top: 0; margin-bottom: 12px; line-height: 150%; }}
h1 {{ font-size: 24pt; font-weight: 600; margin-top: 12px; margin-bottom: 16px; }}
h2 {{ font-size: 19pt; font-weight: 600; margin-top: 22px; margin-bottom: 12px; }}
h3 {{ font-size: 16pt; font-weight: 600; margin-top: 18px; margin-bottom: 10px; }}
h4 {{ font-size: 13.5pt; font-weight: 600; margin-top: 16px; margin-bottom: 8px; }}
h5 {{ font-size: 11.5pt; font-weight: 600; margin-top: 14px; margin-bottom: 6px; }}
h6 {{ color: #57606a; font-size: 10.5pt; font-weight: 600; margin-top: 14px; margin-bottom: 6px; }}
ul, ol {{ margin-top: 4px; margin-bottom: 12px; }}
li {{ margin-bottom: 1px; }}
blockquote {{ color: #57606a; background-color: #f6f8fa; border-left: 3px solid #d0d7de; margin: 10px 0 14px 4px; padding: 6px 10px 6px 14px; }}
a {{ color: #0969da; text-decoration: none; }}
code {{ background-color: #f1f3f5; color: #1f2328; font-family: \"{code}\"; font-size: 10pt; }}
pre {{ background-color: #f6f8fa; border: 1px solid #d8dee4; margin: 10px 0 16px 0; padding: 12px; white-space: pre-wrap; }}
pre code {{ background-color: transparent; }}
hr {{ background-color: #d8dee4; border: none; height: 1px; margin: 20px 0; }}
table {{ border-collapse: collapse; margin: 10px 0 16px 0; }}
th {{ background-color: #f6f8fa; font-weight: 600; padding: 9px 12px; border: 1px solid #d0d7de; }}
td {{ padding: 9px 12px; border: 1px solid #d0d7de; }}
""".strip()


def window_gutter(width: int) -> int:
    return LARGE_WINDOW_GUTTER if width >= GUTTER_BREAKPOINT else SMALL_WINDOW_GUTTER


def apply_document_style(
    document: QTextDocument, palette: QPalette, markdown: str = ""
) -> None:
    """Style the structures produced by Qt's Markdown parser."""
    dark = palette.color(QPalette.ColorRole.Base).lightness() < 128
    text = QColor("#e6edf3" if dark else "#24292f")
    muted = QColor("#9da7b1" if dark else "#57606a")
    subtle = QColor("#252b31" if dark else "#f6f8fa")
    inline_bg = QColor("#30363d" if dark else "#eff1f3")
    border = QColor("#444c56" if dark else "#d0d7de")
    link = QColor("#58a6ff" if dark else "#0969da")
    heading_sizes = {1: 24.0, 2: 19.0, 3: 16.0, 4: 13.5, 5: 11.5, 6: 10.5}

    document.setDefaultFont(document_font())
    fenced_blocks = []
    block = document.begin()
    while block.isValid():
        block_format = block.blockFormat()
        heading = block_format.headingLevel()
        fenced = bool(
            block_format.property(QTextFormat.Property.BlockNonBreakableLines)
        )
        quoted = bool(block_format.property(QTextFormat.Property.BlockQuoteLevel))
        block_format.setLineHeight(
            150, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
        )
        block_format.setBottomMargin(10)
        if heading:
            block_format.setTopMargin(18 if heading > 1 else 10)
            block_format.setBottomMargin(10 if heading > 1 else 14)
        if quoted:
            block_format.setLeftMargin(15)
            block_format.setRightMargin(6)
            block_format.setBackground(subtle)
        if fenced:
            fenced_blocks.append(block)
            # QTextBlock backgrounds cover the natural line box but not extra
            # proportional leading. A 100% code line height makes adjacent
            # lines meet as one panel instead of appearing as separate strips.
            block_format.setLineHeight(
                100, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value
            )
            block_format.setLeftMargin(12)
            block_format.setRightMargin(12)
            block_format.setTopMargin(0)
            block_format.setBottomMargin(0)
            block_format.setBackground(subtle)
        if block.textList() is not None:
            block_format.setBottomMargin(2)
        QTextCursor(block).setBlockFormat(block_format)

        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            char_format = fragment.charFormat()
            char_format.setForeground(muted if quoted else text)
            if heading:
                char_format.setFontPointSize(heading_sizes[heading])
                char_format.setFontWeight(QFont.Weight.DemiBold)
                if heading == 6:
                    char_format.setForeground(muted)
            if char_format.isAnchor():
                char_format.setForeground(link)
                char_format.setFontUnderline(False)
            if fenced or char_format.fontFixedPitch():
                char_format.setFontFamilies([code_font_family()])
                char_format.setFontPointSize(10)
                if not fenced:
                    char_format.setBackground(inline_bg)
            fragment_cursor = QTextCursor(document)
            fragment_cursor.setPosition(fragment.position())
            fragment_cursor.setPosition(
                fragment.position() + fragment.length(), QTextCursor.MoveMode.KeepAnchor
            )
            fragment_cursor.setCharFormat(char_format)
            iterator += 1
        block = block.next()

    def style_frame(frame: QTextFrame) -> None:
        for child in frame.childFrames():
            if isinstance(child, QTextTable):
                table_format = child.format()
                table_format.setBorder(1)
                table_format.setBorderBrush(border)
                table_format.setCellPadding(9)
                table_format.setCellSpacing(0)
                child.setFormat(table_format)
            style_frame(child)

    style_frame(document.rootFrame())

    # Qt discards fence info strings. Match source fences to its fenced blocks
    # in order, then colour only their existing selectable character ranges.
    cursor = 0
    for fence in find_code_fences(markdown):
        count = len(fence.lines)
        blocks = fenced_blocks[cursor : cursor + count]
        cursor += count
        if not blocks:
            continue
        first_format = blocks[0].blockFormat()
        first_format.setTopMargin(9)
        QTextCursor(blocks[0]).setBlockFormat(first_format)
        last_format = blocks[-1].blockFormat()
        last_format.setBottomMargin(9)
        QTextCursor(blocks[-1]).setBlockFormat(last_format)
        apply_syntax_highlighting(document, blocks, fence.language, dark)
