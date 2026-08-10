"""Selection-aware Markdown serialization for the live Qt document."""

from __future__ import annotations

import re

from PySide6.QtCore import QByteArray, QMimeData
from PySide6.QtGui import QFont, QTextBlock, QTextCursor, QTextListFormat, QTextFormat

from .document_regions import DocumentRegions


def _escape(text: str, *, block_start: bool = False) -> str:
    text = re.sub(r"([\\`*_[\]])", r"\\\1", text)
    if block_start:
        text = re.sub(r"^(#{1,6}|>|[-+*](?=\s)|\d+[.)](?=\s))", r"\\\1", text)
    return text


def _code_span(text: str) -> str:
    longest = max((len(x) for x in re.findall(r"`+", text)), default=0)
    fence = "`" * max(1, longest + 1)
    padding = " " if text.startswith(("`", " ")) or text.endswith(("`", " ")) else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def _link_destination(url: str) -> str:
    return url.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _inline(block: QTextBlock, start: int, end: int) -> str:
    parts: list[str] = []
    iterator = block.begin()
    while not iterator.atEnd():
        fragment = iterator.fragment()
        left = max(start, fragment.position())
        right = min(end, fragment.position() + fragment.length())
        if left < right:
            text = fragment.text()[left - fragment.position() : right - fragment.position()]
            fmt = fragment.charFormat()
            if "\ufffc" in text and fmt.isImageFormat():
                image = fmt.toImageFormat()
                alt = image.property(QTextFormat.Property.ImageAltText) or ""
                rendered = f"![{_escape(str(alt))}]({_link_destination(image.name())})"
            elif fmt.fontFixedPitch():
                rendered = _code_span(text)
            else:
                rendered = _escape(text)
                if fmt.fontStrikeOut():
                    rendered = f"~~{rendered}~~"
                if fmt.fontItalic():
                    rendered = f"*{rendered}*"
                if fmt.fontWeight() >= QFont.Weight.Bold:
                    rendered = f"**{rendered}**"
                if fmt.isAnchor() and fmt.anchorHref():
                    rendered = f"[{rendered}]({_link_destination(fmt.anchorHref())})"
            parts.append(rendered)
        iterator += 1
    return "".join(parts)


def _fence(code: str, language: str | None) -> str:
    longest = max((len(x) for x in re.findall(r"`+", code)), default=0)
    marker = "`" * max(3, longest + 1)
    body = code.rstrip("\r\n")
    return f"{marker}{language or ''}\n{body}\n{marker}"


def _list_prefix(block: QTextBlock) -> str:
    text_list = block.textList()
    if text_list is None:
        return ""
    fmt = text_list.format()
    indent = "  " * max(0, fmt.indent() - 1)
    style = fmt.style()
    ordered = style in (
        QTextListFormat.Style.ListDecimal, QTextListFormat.Style.ListLowerAlpha,
        QTextListFormat.Style.ListUpperAlpha, QTextListFormat.Style.ListLowerRoman,
        QTextListFormat.Style.ListUpperRoman,
    )
    if ordered:
        number = fmt.start() + text_list.itemNumber(block)
        return f"{indent}{number}. "
    marker = "-"
    checked = block.blockFormat().marker()
    if checked == block.blockFormat().MarkerType.Checked:
        return f"{indent}{marker} [x] "
    if checked == block.blockFormat().MarkerType.Unchecked:
        return f"{indent}{marker} [ ] "
    return f"{indent}{marker} "


def _serialize_blocks(cursor: QTextCursor, regions: DocumentRegions) -> str:
    start, end = cursor.selectionStart(), cursor.selectionEnd()
    lines: list[tuple[str, bool]] = []
    block = cursor.document().findBlock(start)
    while block.isValid() and block.position() < end:
        left = max(start, block.position())
        right = min(end, block.position() + len(block.text()))
        code = next((r for r in regions.code_blocks if r.rendered_start <= left and right <= r.rendered_end), None)
        if code is not None:
            code_start = max(0, left - code.rendered_start)
            code_end = max(code_start, right - code.rendered_start)
            language = None
            lines.append((_fence(block.text()[left-block.position():right-block.position()], language), True))
            while block.next().isValid() and block.next().position() < end and code.contains(block.next().position()):
                # Multiple code lines are combined below by replacing this entry.
                nxt = block.next(); right2 = min(end, nxt.position() + len(nxt.text()))
                selected = "\n".join(_blocks_between(block, nxt, start, end))
                lines[-1] = (_fence(selected, None), True); block = nxt
        else:
            content = _inline(block, left, right)
            heading = block.blockFormat().headingLevel()
            prefix = f"{'#' * heading} " if heading else _list_prefix(block)
            quote = "> " * int(block.blockFormat().property(QTextFormat.Property.BlockQuoteLevel) or 0)
            lines.append((quote + prefix + content, bool(heading or prefix or quote)))
        block = block.next()
    output: list[str] = []
    for value, structural in lines:
        if not value and output and output[-1] != "":
            output.append("")
        elif value:
            if output and not structural and output[-1] and not output[-1].startswith(("- ", "> ", "#")):
                output.append("")
            output.append(value)
    return "\n".join(output).strip("\n")


def _blocks_between(first: QTextBlock, last: QTextBlock, start: int, end: int):
    block = first
    while block.isValid():
        left, right = max(start, block.position()), min(end, block.position() + len(block.text()))
        yield block.text()[left-block.position():right-block.position()]
        if block == last:
            break
        block = block.next()


def selected_markdown(cursor: QTextCursor, source: str, regions: DocumentRegions) -> str | None:
    """Return Markdown for a non-empty rendered selection, without mutating it."""
    if not cursor.hasSelection():
        return None
    document = cursor.document()
    if cursor.selectionStart() == 0 and cursor.selectionEnd() == document.characterCount() - 1:
        return source
    for code in regions.code_blocks:
        if code.rendered_start <= cursor.selectionStart() and cursor.selectionEnd() <= code.rendered_end:
            if cursor.selectionStart() == code.rendered_start and cursor.selectionEnd() == code.rendered_end:
                return source[code.source_start:code.source_end].rstrip("\r\n")
            selected = cursor.selectedText().replace("\u2029", "\n").replace("\u2028", "\n")
            selected = selected.replace("\ufdd0", "").replace("\ufdd1", "")
            return _fence(selected, code.language)
    for heading in regions.headings:
        if cursor.selectionStart() == heading.rendered_start and cursor.selectionEnd() == heading.rendered_end:
            if heading.source_start is not None:
                following = next((h for h in regions.headings if h.rendered_start == heading.rendered_end), None)
                source_end = following.source_start if following and following.source_start is not None else len(source)
                return source[heading.source_start:source_end].rstrip("\r\n")
    return _serialize_blocks(cursor, regions)


def markdown_mime_data(cursor: QTextCursor, source: str, regions: DocumentRegions) -> QMimeData | None:
    markdown = selected_markdown(cursor, source, regions)
    if markdown is None:
        return None
    data = QMimeData()
    data.setText(markdown)
    data.setData("text/markdown", QByteArray(markdown.encode("utf-8")))
    return data
