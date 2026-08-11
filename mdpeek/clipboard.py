"""Clipboard conversion for selections in MDPeek's rendered document."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from html import escape

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QTextCursor, QTextDocumentFragment


def selected_plain_text(cursor: QTextCursor) -> str:
    """Return visible selected text with native line separators."""
    if not cursor.hasSelection():
        return ""
    text = QTextDocumentFragment(cursor).toPlainText()
    text = text.replace("\u2029", "\n").replace("\u2028", "\n")
    text = text.replace("\ufdd0", "").replace("\ufdd1", "")
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", os.linesep)


def _span_html(element: ET.Element, *, in_panel: bool) -> str:
    content = escape(element.text or "") + "".join(_clean_node(child, in_panel=in_panel) for child in element)
    style = element.attrib.get("style", "").lower()
    wrapper = None
    if not in_panel:
        if "font-weight:700" in style or "font-weight:600" in style:
            wrapper = "strong"
        elif "font-style:italic" in style:
            wrapper = "em"
        elif "line-through" in style:
            wrapper = "del"
        elif "font-family:" in style:
            wrapper = "code"
    result = f"<{wrapper}>{content}</{wrapper}>" if wrapper else content
    return result + escape(element.tail or "")


def _clean_node(element: ET.Element, *, in_panel: bool = False) -> str:
    tag = element.tag.lower()
    if tag == "span":
        return _span_html(element, in_panel=in_panel)
    allowed = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "a", "img", "hr", "br", "table", "tr", "td", "th", "pre", "blockquote", "strong", "em", "del", "code"}
    if tag not in allowed:
        content = escape(element.text or "") + "".join(_clean_node(child, in_panel=in_panel) for child in element)
        return content + escape(element.tail or "")
    attrs = ""
    if tag == "a" and "href" in element.attrib:
        attrs = f' href="{escape(element.attrib["href"], quote=True)}"'
    elif tag == "img":
        values = [f'{name}="{escape(element.attrib[name], quote=True)}"' for name in ("src", "alt") if name in element.attrib]
        attrs = (" " + " ".join(values)) if values else ""
    if tag in {"img", "hr", "br"}:
        return f"<{tag}{attrs}>" + escape(element.tail or "")
    child_panel = in_panel or tag.startswith("h")
    if tag == "table":
        rows = list(element.findall("tr"))
        rendered_rows = []
        for row_index, row in enumerate(rows):
            cells = []
            for cell in row:
                cell_tag = "th" if row_index == 0 else "td"
                inner = escape(cell.text or "") + "".join(_clean_node(node, in_panel=row_index == 0) for node in cell)
                cells.append(f"<{cell_tag}>{inner}</{cell_tag}>")
            rendered_rows.append(f"<tr>{''.join(cells)}</tr>")
        return f"<table>{''.join(rendered_rows)}</table>" + escape(element.tail or "")
    content = escape(element.text or "") + "".join(_clean_node(child, in_panel=child_panel) for child in element)
    return f"<{tag}{attrs}>{content}</{tag}>" + escape(element.tail or "")


def _panel_html(table: ET.Element) -> str:
    serialized = ET.tostring(table, encoding="unicode")
    if "font-family:" in serialized:
        paragraphs = list(table.iter("p"))
        code = "\n".join("".join(paragraph.itertext()) for paragraph in paragraphs)
        # A frame immediately following another MDPeek panel gains one Qt
        # boundary spacer; it is not part of the rendered Markdown code.
        code = code.removeprefix(" ")
        return f"<pre><code>{escape(code)}</code></pre>"
    paragraphs = [_clean_node(node) for node in table.iter() if node.tag.lower() == "p"]
    return f"<blockquote>{''.join(paragraphs)}</blockquote>"


_CONTAINER_TAGS = {"ul", "ol", "table", "tr", "blockquote"}
_BLOCK_TAGS = _CONTAINER_TAGS | {"li", "td", "th", "p", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}
_VOID_TAGS = {"br", "hr", "img"}


def _opening_tag(element: ET.Element) -> str:
    attributes = "".join(
        f' {name}="{escape(value, quote=True)}"'
        for name, value in element.attrib.items()
    )
    return f"<{element.tag}{attributes}>"


def _inline_html(element: ET.Element) -> str:
    opening = _opening_tag(element)
    if element.tag in _VOID_TAGS:
        result = opening
    else:
        content = escape(element.text or "")
        content += "".join(_inline_html(child) for child in element)
        result = f"{opening}{content}</{element.tag}>"
    return result + escape(element.tail or "")


def _pretty_node(element: ET.Element, level: int) -> str:
    indent = "    " * level
    tag = element.tag
    if tag in _VOID_TAGS or tag == "pre":
        return indent + _inline_html(element).rstrip()

    children = list(element)
    structural = tag in _CONTAINER_TAGS or any(
        child.tag in _BLOCK_TAGS for child in children
    )
    if not structural:
        return indent + _inline_html(element).rstrip()

    opening = _opening_tag(element)
    inline_prefix = escape(element.text or "")
    lines: list[str] = []
    block_children: list[ET.Element] = []
    for child in children:
        if child.tag in _BLOCK_TAGS:
            block_children.append(child)
        else:
            inline_prefix += _inline_html(child)

    if inline_prefix.strip():
        lines.append(f"{indent}{opening}{inline_prefix.rstrip()}")
    else:
        lines.append(f"{indent}{opening}")
    lines.extend(_pretty_node(child, level + 1) for child in block_children)
    lines.append(f"{indent}</{tag}>{escape(element.tail or '').rstrip()}")
    return "\n".join(lines)


def format_html_fragment(fragment: str) -> str:
    """Indent block structure without adding whitespace to inline content."""
    xhtml = re.sub(r"<(br|hr|img)(\b[^>]*)>", r"<\1\2 />", fragment)
    root = ET.fromstring(f"<fragment>{xhtml}</fragment>")
    return "\n".join(_pretty_node(child, 0) for child in root)


def selected_clean_html(cursor: QTextCursor) -> str:
    """Normalize Qt's selected fragment to small semantic HTML."""
    if not cursor.hasSelection():
        return ""
    raw = QTextDocumentFragment(cursor).toHtml()
    root = ET.fromstring(raw[raw.index("<html"):])
    body = root.find("body")
    if body is None:
        return ""
    output: list[str] = []
    for child in body:
        empty_pre = child.tag.lower() == "pre" and not "".join(child.itertext()).strip()
        empty_paragraph = child.tag.lower() == "p" and list(child) and all(node.tag.lower() == "br" for node in child)
        if empty_pre or empty_paragraph:
            continue
        if child.tag.lower() == "table" and "-qt-table-type: frame" in child.attrib.get("style", ""):
            output.append(_panel_html(child))
        else:
            output.append(_clean_node(child))
    fragment = re.sub(r">\s+<", "><", "".join(output).strip())
    return format_html_fragment(fragment)


def plain_mime_data(cursor: QTextCursor) -> QMimeData | None:
    if not cursor.hasSelection():
        return None
    data = QMimeData()
    data.setText(selected_plain_text(cursor))
    return data


def html_source_mime_data(cursor: QTextCursor) -> QMimeData | None:
    if not cursor.hasSelection():
        return None
    fragment = selected_clean_html(cursor)
    data = QMimeData()
    data.setHtml(fragment)
    # Set the primary plain-text representation last. On Windows, some Qt
    # versions otherwise expose an empty text value after ownership transfer.
    data.setText(fragment)
    return data


def markdown_for_complete_selection(cursor: QTextCursor, source: str) -> str | None:
    """Reliable Phase 5 seed: return source only for a complete selection."""
    document = cursor.document()
    complete = cursor.hasSelection() and cursor.selectionStart() == 0 and cursor.selectionEnd() == document.characterCount() - 1
    return source if complete else None
