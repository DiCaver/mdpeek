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

Press `Ctrl+P` (or choose **File > Print…**) to open Qt's full-document print preview. Printing uses a separate, paper-sized document with a white background, dark text, underlined links, restrained code and quote panels, and printer-derived margins; the responsive on-screen gutter is not printed. The preview includes the complete rendered document even when text is selected or the viewer is scrolled, and uses the operating system's native printer selection. The welcome screen cannot be printed.

To create a PDF on Windows through the standard print workflow:

1. Open Print with `Ctrl+P`.
2. Choose the print command from the preview.
3. Select **Microsoft Print to PDF**.
4. Choose the destination filename in the Windows dialog.

MDPeek does not implement a separate PDF exporter; Windows supplies the PDF printer and filename prompt.

Use **File > Back** (`Alt+Left`) and **File > Forward** (`Alt+Right`) to revisit files opened during the current session. MDPeek remembers each visit's vertical reading position and reloads the file from disk when navigating, so external edits are visible. Like a browser, opening another file after going Back replaces the forward branch; refreshing the current file does not. If a historical file has been moved, deleted, or become unreadable, MDPeek reports the error while leaving the current document and complete history intact so navigation can be retried. History belongs to one window and is discarded when MDPeek closes.

The resizable **Document Outline** sidebar displays rendered H1–H6 headings as a hierarchy. Click a heading to scroll to that exact occurrence; repeated titles remain separate, and the item for the section at the top of the reading area is highlighted as you scroll. Long titles are elided with their full text in a tooltip, empty headings use an untitled fallback, and a document with no headings shows a quiet message. Collapse branches with their disclosure controls. Use `Ctrl+H` or **View > Document Outline** to show or hide the sidebar; its visibility and width are retained while the application is running.

Selection commands are available from both the **Edit** menu and the document context menu:

- `Ctrl+A` selects the rendered document.
- `Ctrl+C` copies the selected visible text as plain text.
- `Ctrl+Shift+C` copies the selection as clean semantic HTML source.
- `Ctrl+Shift+M` copies the selection as balanced Markdown.

| Command | Clipboard result |
| --- | --- |
| Copy | Rendered plain text |
| Copy as HTML | Clean HTML plus plain-text fallback |
| Copy as Markdown | Selection represented as Markdown |

**Copy as Markdown** preserves headings, emphasis, links, lists, quotes, code, tables, and other available Markdown structure. Partial formatted selections receive balanced delimiters, while `Ctrl+A` uses the exact loaded source—including source-only definitions, comments, and original whitespace—where possible. The command is available in the Edit menu and, with the other two formats, in the document context menu.

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

MDPeek provides a single read-only, selectable document window using Qt's built-in Markdown renderer. External links open in the system browser and relative images resolve from the currently open Markdown file's folder. Editing, tabs, recent files, automatic file watching, file associations, themes, and installers are outside the current scope.

## License

MDPeek is released under the [MIT License](LICENSE).
