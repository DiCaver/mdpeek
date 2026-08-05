# MDPeek

A tiny, read-only Markdown viewer built with Python and PySide6.

Phase 1 opens and renders a UTF-8 Markdown file supplied on the command line. Start it without a file to see a short usage hint. There are intentionally no editing features.

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

## Test

```powershell
python -m unittest discover -s tests
```

## Scope

MDPeek currently provides a single read-only window using Qt's built-in Markdown renderer. File associations, richer Markdown extensions, themes, and copy-format options are future work.

## License

MDPeek is released under the [MIT License](LICENSE).
