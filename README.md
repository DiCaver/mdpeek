# MDPeek

A tiny, read-only Markdown viewer built with Python and PySide6.

MDPeek opens and renders UTF-8 Markdown files from the command line, the native Open dialog, or drag-and-drop. There are intentionally no editing features.

The viewer includes a clean reading layout, responsive document margins, offline Pygments highlighting, and selection copying while retaining Qt's small built-in Markdown renderer.

## Setup

MDPeek requires Python 3.10 or newer. From the repository root, create a virtual environment and install the application:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Run

Open a Markdown file:

```powershell
mdpeek README.md
```

Or run the package directly:

```powershell
python -m mdpeek README.md
```

Running either command without a filepath opens the empty screen. Close the window to exit.

While MDPeek is running, press `Ctrl+O` (or choose **File > Open…**) to select a file. You can also drag one `.md` or `.markdown` file anywhere onto the window. A newly opened file replaces the current document in the same window; MDPeek remains a read-only viewer.

Selection commands are available from both the **Edit** menu and the document context menu:

- `Ctrl+A` selects the rendered document.
- `Ctrl+C` copies the selected visible text as plain text.
- `Ctrl+Shift+C` copies the selection as clean semantic HTML source.

Move the pointer over a rendered heading to reveal its **Select section** control. It selects the heading and everything below it, including nested subsections, stopping immediately before the next heading of the same or a higher level (or at the end of the document). Selecting does not copy or change the document; use the existing plain-text or HTML command afterward. **Edit > Select Current Section** provides the same operation for the section containing the text cursor or the start of the current selection.

Move the pointer over a fenced code block to reveal **Copy code**. It copies immediately as plain text, using the original source code rather than highlighted document text: fences, the language label, highlighting markup, and viewer-added spacing are excluded. **Edit > Copy Current Code Block** is available when the text cursor or selection begins inside a fenced block.

**Copy as HTML** puts literal HTML markup in the clipboard's primary `text/plain` value for VS Code, HTML editors, and CMS source fields. The identical clean fragment is also exposed as `text/html` for rich-text applications. It contains semantic document elements but no MDPeek CSS, syntax-highlighting spans, or Qt document wrapper.

To explore the supported Markdown and presentation styles, open the included showcase:

```powershell
python -m mdpeek examples/showcase.md
```

## Markdown support

Qt correctly renders headings, emphasis, strikethrough, links, ordered and unordered lists, blockquotes, inline and fenced code, tables, horizontal rules, Unicode text, and relative local images used by the showcase.

Its built-in renderer intentionally supports a practical CommonMark/GitHub-style subset rather than every Markdown extension. Task lists render as non-interactive checked and unchecked boxes. MDPeek adds syntax highlighting for recognized fenced-code language labels; unknown and unlabeled fences remain ordinary monospace code. Table alignment hints may not affect presentation, and raw HTML/CSS support is limited. MDPeek does not use a browser engine, JavaScript, remote themes, or CDNs.

## Test

```powershell
python -m unittest discover -s tests
```

## Scope

MDPeek provides a single read-only, selectable document window using Qt's built-in Markdown renderer. External links open in the system browser and relative images resolve from the currently open Markdown file's folder. Editing, tabs, recent files, automatic file watching, file associations, themes, and installers are outside the current scope. Copy as Markdown remains planned; it is not generally available because partial rendered selections cannot yet be mapped reliably to exact source ranges.

## Copy as Markdown investigation

Qt retains useful rendered structure and character formatting (including heading levels, lists, links, tables, and code-block flags), but it does not retain original Markdown source offsets. Direct cursor-to-source position mapping breaks as punctuation disappears or text transforms in headings, emphasis, links, lists, tables, fenced code, and entities; MDPeek's panel styling also inserts document frame markers around quotes and code. Unicode survives rendering, but its rendered offset is not enough to recover surrounding source syntax.

For Phase 5, the recommended approach is to record source ranges while parsing Markdown and associate them with rendered ranges before presentation styling. A source-to-render mapping therefore appears necessary for reliable partial Copy as Markdown. Phase 4 stores the exact current source and includes only the reliable internal special case: a complete rendered-document selection maps back to that exact source.

## License

MDPeek is released under the [MIT License](LICENSE).
