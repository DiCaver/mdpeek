# MDPeek

A tiny, read-only Markdown viewer built with Python and PySide6.

MDPeek opens and renders a UTF-8 Markdown file supplied on the command line. Start it without a file to see a short usage hint. There are intentionally no editing features.

Phase 2 adds a clean reading layout, responsive document margins, modern Windows font selection, restrained styling, and offline Pygments highlighting for fenced code while retaining Qt's small built-in Markdown renderer.

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

MDPeek provides a single read-only, selectable document window using Qt's built-in Markdown renderer. External links open in the system browser and relative images resolve from the Markdown file's folder. Editing, drag-and-drop, file associations, themes, installers, and copy-as-Markdown are outside the current scope.

## License

MDPeek is released under the [MIT License](LICENSE).
