"""Fenced-code discovery and restrained Pygments formatting."""

from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtGui import QColor, QTextBlock, QTextCharFormat, QTextCursor, QTextDocument
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Keyword, Literal, Name, Number, Operator, String
from pygments.util import ClassNotFound


_FENCE_START = re.compile(r"^(?P<indent> {0,3})(?P<marker>`{3,}|~{3,})(?P<info>.*)$")
_ALIASES = {
    "js": "javascript", "ts": "typescript", "cs": "csharp", "py": "python",
    "ps1": "powershell", "sh": "bash",
}


@dataclass(frozen=True)
class CodeFence:
    language: str | None
    lines: tuple[str, ...]


def find_code_fences(markdown: str) -> list[CodeFence]:
    """Return closed fenced blocks without changing their code text."""
    lines = markdown.splitlines()
    fences: list[CodeFence] = []
    index = 0
    while index < len(lines):
        match = _FENCE_START.match(lines[index])
        if match is None:
            index += 1
            continue
        marker = match.group("marker")
        info = match.group("info").strip()
        if marker[0] == "`" and "`" in info:
            index += 1
            continue
        language = info.split(maxsplit=1)[0].lower() if info else None
        closing = re.compile(rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*$")
        code_lines: list[str] = []
        index += 1
        while index < len(lines) and closing.match(lines[index]) is None:
            code_lines.append(lines[index])
            index += 1
        # CommonMark treats a fence that reaches EOF as implicitly closed.
        fences.append(CodeFence(language, tuple(code_lines)))
        if index < len(lines):
            index += 1
    return fences


def lexer_for_language(language: str | None):  # type: ignore[no-untyped-def]
    if not language:
        return None
    try:
        return get_lexer_by_name(_ALIASES.get(language.lower(), language.lower()), stripnl=False)
    except ClassNotFound:
        return None


def _token_color(token, dark: bool) -> QColor | None:  # type: ignore[no-untyped-def]
    colors = {
        "comment": "#6a9955" if dark else "#687078",
        "keyword": "#569cd6" if dark else "#76507f",
        "string": "#ce9178" if dark else "#586b35",
        "number": "#b5cea8" if dark else "#825d2f",
        "name": "#4ec9b0" if dark else "#35677d",
        "operator": "#d4d4d4" if dark else "#59636e",
    }
    if token in Comment:
        return QColor(colors["comment"])
    if token in Keyword:
        return QColor(colors["keyword"])
    if token in String:
        return QColor(colors["string"])
    if token in Number or token in Literal:
        return QColor(colors["number"])
    if token in Name.Function or token in Name.Class or token in Name.Tag or token in Name.Builtin:
        return QColor(colors["name"])
    if token in Operator:
        return QColor(colors["operator"])
    return None


def apply_syntax_highlighting(
    document: QTextDocument,
    blocks: list[QTextBlock],
    language: str | None,
    dark: bool,
) -> bool:
    """Colour a rendered fence in place; return whether a lexer was found."""
    lexer = lexer_for_language(language)
    if lexer is None or not blocks:
        return False
    code = "\n".join(block.text() for block in blocks)
    offsets: list[tuple[int, int, QTextBlock]] = []
    offset = 0
    for block in blocks:
        offsets.append((offset, offset + len(block.text()), block))
        offset += len(block.text()) + 1

    position = 0
    for token, value in lex(code, lexer):
        color = _token_color(token, dark)
        start, end = position, position + len(value)
        position = end
        if color is None:
            continue
        for block_start, block_end, block in offsets:
            left, right = max(start, block_start), min(end, block_end)
            if left >= right:
                continue
            cursor = QTextCursor(document)
            cursor.setPosition(block.position() + left - block_start)
            cursor.setPosition(block.position() + right - block_start, QTextCursor.MoveMode.KeepAnchor)
            char_format = QTextCharFormat()
            char_format.setForeground(color)
            cursor.mergeCharFormat(char_format)
    return True
