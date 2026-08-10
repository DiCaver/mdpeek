"""Source and rendered regions used by MDPeek's document interactions."""

from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtGui import QTextBlock, QTextDocument, QTextFormat

from .style import CODE_PANEL, PANEL_KIND_PROPERTY


_FENCE_START = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>`{3,}|~{3,})(?P<info>[^\r\n]*)(?P<eol>\r\n|\n|\r|$)"
)
_ATX_HEADING = re.compile(r"^ {0,3}(?P<marks>#{1,6})(?:[ \t]+|$)")
_SETEXT_HEADING = re.compile(r"^ {0,3}(?P<marks>=+|-+)[ \t]*$")


@dataclass(frozen=True)
class SourceHeading:
    level: int
    start: int
    end: int


@dataclass(frozen=True)
class SourceCodeFence:
    language: str | None
    start: int
    end: int
    code_start: int
    code_end: int
    code: str


@dataclass(frozen=True)
class HeadingRegion:
    level: int
    rendered_start: int
    rendered_end: int
    title: str = ""
    source_start: int | None = None
    source_end: int | None = None

    def contains(self, position: int) -> bool:
        return self.rendered_start <= position < self.rendered_end


@dataclass(frozen=True)
class CodeRegion:
    rendered_start: int
    rendered_end: int
    code: str
    source_start: int
    source_end: int
    language: str | None = None

    def contains(self, position: int) -> bool:
        return self.rendered_start <= position < self.rendered_end


@dataclass(frozen=True)
class DocumentRegions:
    headings: tuple[HeadingRegion, ...] = ()
    code_blocks: tuple[CodeRegion, ...] = ()

    def heading_at(self, position: int) -> HeadingRegion | None:
        return next((region for region in reversed(self.headings) if region.contains(position)), None)

    def code_at(self, position: int) -> CodeRegion | None:
        return next((region for region in self.code_blocks if region.contains(position)), None)


def _lines_with_offsets(markdown: str) -> list[tuple[int, str, str]]:
    result = []
    offset = 0
    for complete in markdown.splitlines(keepends=True):
        text = complete.rstrip("\r\n")
        result.append((offset, text, complete))
        offset += len(complete)
    if offset < len(markdown) or not result:
        result.append((offset, markdown[offset:], markdown[offset:]))
    return result


def scan_source_headings(markdown: str) -> list[SourceHeading]:
    """Find CommonMark ATX/setext headings outside fenced code."""
    lines = _lines_with_offsets(markdown)
    headings: list[SourceHeading] = []
    fence_char: str | None = None
    fence_length = 0
    for index, (offset, text, complete) in enumerate(lines):
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", text)
        if fence:
            marker = fence.group(1)
            if fence_char is None and not (marker[0] == "`" and "`" in fence.group(2)):
                fence_char, fence_length = marker[0], len(marker)
                continue
            if fence_char == marker[0] and len(marker) >= fence_length and not fence.group(2).strip():
                fence_char = None
                continue
        if fence_char is not None:
            continue
        atx = _ATX_HEADING.match(text)
        if atx:
            headings.append(SourceHeading(len(atx.group("marks")), offset, offset + len(complete)))
            continue
        if index and text and _SETEXT_HEADING.match(text):
            previous_offset, previous, previous_complete = lines[index - 1]
            if previous.strip():
                level = 1 if text.lstrip().startswith("=") else 2
                headings.append(SourceHeading(level, previous_offset, offset + len(complete)))
    return headings


def scan_source_code_fences(markdown: str) -> list[SourceCodeFence]:
    """Return exact fence payloads, applying only CommonMark fence indentation."""
    lines = _lines_with_offsets(markdown)
    fences: list[SourceCodeFence] = []
    index = 0
    while index < len(lines):
        offset, _text, complete = lines[index]
        opening = _FENCE_START.match(complete)
        if opening is None or (opening.group("marker")[0] == "`" and "`" in opening.group("info")):
            index += 1
            continue
        marker = opening.group("marker")
        indent = len(opening.group("indent"))
        info = opening.group("info").strip()
        language = info.split(maxsplit=1)[0].lower() if info else None
        close = re.compile(rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*(?:\r\n|\n|\r|$)")
        content: list[str] = []
        code_start = offset + len(complete)
        code_end = code_start
        index += 1
        while index < len(lines) and close.match(lines[index][2]) is None:
            line_offset, _line_text, raw = lines[index]
            remove = min(indent, len(raw) - len(raw.lstrip(" ")))
            content.append(raw[remove:])
            code_end = line_offset + len(raw)
            index += 1
        end = lines[index][0] + len(lines[index][2]) if index < len(lines) else len(markdown)
        fences.append(SourceCodeFence(language, offset, end, code_start, code_end, "".join(content)))
        if index < len(lines):
            index += 1
    return fences


def build_document_regions(document: QTextDocument, markdown: str) -> DocumentRegions:
    """Associate stable source regions with Qt's rendered ranges in order."""
    source_headings = scan_source_headings(markdown)
    rendered_headings: list[tuple[int, QTextBlock]] = []
    block = document.begin()
    while block.isValid():
        level = block.blockFormat().headingLevel()
        if level:
            rendered_headings.append((level, block))
        block = block.next()

    headings: list[HeadingRegion] = []
    document_end = max(0, document.characterCount() - 1)
    for index, (level, heading_block) in enumerate(rendered_headings):
        end = document_end
        for next_level, next_block in rendered_headings[index + 1 :]:
            if next_level <= level:
                end = next_block.position()
                break
        source = source_headings[index] if index < len(source_headings) else None
        headings.append(HeadingRegion(
            level, heading_block.position(), end, heading_block.text(),
            source.start if source and source.level == level else None,
            source.end if source and source.level == level else None,
        ))

    panels = sorted(
        (frame for frame in document.rootFrame().childFrames()
         if frame.format().property(PANEL_KIND_PROPERTY) == CODE_PANEL),
        key=lambda frame: frame.firstPosition(),
    )
    # Qt produces no fenced QTextBlock at all for a completely empty fence.
    # Exclude those source entries so a later visible panel cannot be paired
    # with the wrong raw payload. A fence containing a blank line has code
    # ``"\n"`` and does produce a panel, so it remains interactive.
    sources = [source for source in scan_source_code_fences(markdown) if source.code]
    code_blocks = tuple(
        CodeRegion(frame.firstPosition(), frame.lastPosition(), source.code, source.start, source.end, source.language)
        for frame, source in zip(panels, sources)
    )
    return DocumentRegions(tuple(headings), code_blocks)
