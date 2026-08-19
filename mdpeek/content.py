"""Safe preparation of Markdown before Qt renders it."""

from __future__ import annotations

import re
from html import unescape


_ACTIVE_BLOCK = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.I | re.S)
_EVENT_ATTRIBUTE = re.compile(r"\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
_IMAGE = re.compile(r"<img\b([^>]*)>", re.I)
_ATTRIBUTE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))")


def _safe_fragment(markdown: str) -> str:
    """Return Markdown with common raw HTML converted to Qt-safe Markdown.

    Qt's Markdown importer can consume following Markdown as part of an HTML
    block. Converting the useful portable subset avoids that failure while
    scripts, event handlers and unsupported wrappers are discarded safely.
    """
    text = _ACTIVE_BLOCK.sub("", markdown)
    text = _EVENT_ATTRIBUTE.sub("", text)

    def image(match: re.Match[str]) -> str:
        attrs = {
            name.lower(): unescape(a or b or c or "")
            for name, a, b, c in _ATTRIBUTE.findall(match.group(1))
        }
        source = attrs.get("src", "").strip()
        if not source or source.lower().startswith(("javascript:", "data:text/html")):
            return ""
        alt = attrs.get("alt", "").replace("]", r"\]")
        return f"![{alt}]({source})"

    text = _IMAGE.sub(image, text)
    text = re.sub(r"<kbd\b[^>]*>(.*?)</kbd\s*>", lambda m: f"`{unescape(m.group(1))}`", text, flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", "  \n", text, flags=re.I)
    text = re.sub(r"</?(?:p|div|center|details|summary)\b[^>]*>", "\n\n", text, flags=re.I)
    # Drop remaining tags. Their text stays readable and, critically, later
    # Markdown remains outside an unterminated HTML block.
    text = re.sub(r"</?[A-Za-z][^>]*>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def safe_markdown(markdown: str) -> str:
    """Sanitize prose while preserving fenced code byte-for-byte."""
    parts = re.split(r"((?:^|\n)(?:```|~~~)[^\n]*\n.*?(?:\n(?:```|~~~)[ \t]*(?=\n|$)))", markdown, flags=re.S)
    return "".join(part if index % 2 else _safe_fragment(part) for index, part in enumerate(parts))
