# MDPeek

<!-- <p align="center"><img src="assets/mdpeek-icon.svg" width="112" alt="MDPeek document-and-eye icon"></p> -->

![Screenshot](./assets/mdpeek-icon_small.png)

MDPeek is a small, fast, read-only Markdown viewer for Windows. Double-click a Markdown file, read the rendered preview, select useful content, copy it as plain text, clean HTML, or Markdown, and print through the native Windows print system.

It is deliberately focused, local-first, free, and open source: a viewer for people who do not want to open a full editor just to read a document.

## Why MDPeek?

MDPeek keeps viewing separate from editing. It never modifies the Markdown document and offers a quiet native interface with the navigation and copying tools needed for long technical files.

## Features

- Markdown rendering with syntax-highlighted fenced code
- Document outline, heading navigation, and section selection
- Back and Forward navigation with per-document reading positions
- Copy selections as rendered text, clean HTML, or balanced Markdown
- One-click copying of fenced code blocks
- Local images and supported remote images
- Open dialog, command-line paths, and drag-and-drop opening
- Single-window file opening and automatic refresh after external saves
- Built-in Help available from the Help menu or `F1`
- Native print preview, printer selection, and Microsoft Print to PDF
- Installed and portable Windows x64 editions
- `.md` and `.markdown` Open With integration

MDPeek remains a viewer: there is no editing or tab system.

## Download

Release builds are available from [GitHub Releases](https://github.com/DiCaver/mdpeek/releases).

| Download | Best for |
| --- | --- |
| Windows installer | Normal installation, Start menu shortcut, and optional file registration |
| Portable ZIP | Extracting and running without installation or registry changes |

The first Windows release targets Windows 10/11, 64-bit.

## Installation

1. Download `MDPeek-0.1.0-Windows-x64-Setup.exe` from GitHub Releases.
2. Run the installer.
3. Choose whether to add an optional desktop shortcut and Markdown file registration.
4. Launch MDPeek from the Start menu or open a Markdown file.

The first release is unsigned, so Microsoft Defender SmartScreen may ask you to review the download. Download only from this repository, check the publisher and filename, and verify its SHA-256 hash if desired. Use the warning dialog's normal per-file review path only when you trust and have verified the download; do not disable SmartScreen globally.

## Set MDPeek as the default Markdown viewer

The installer registers MDPeek as an available handler but respects an existing default. If Windows keeps another Markdown application:

1. Right-click a `.md` or `.markdown` file in Explorer.
2. Choose **Open with > Choose another app**.
3. Select **MDPeek**.
4. Enable **Always use this app** where Windows offers that option.

You can also use **Settings > Apps > Default apps**. Windows 10/11 may require explicit confirmation and the installer does not bypass the protected default-app choice.

## Portable version

Extract `MDPeek-0.1.0-Windows-x64-Portable.zip` anywhere and run `MDPeek\MDPeek.exe`. The archive contains the complete one-folder application and does not require Python. Running it does not install files, create shortcuts, or register file associations.

## Using MDPeek

### Opening files

Use **File > Open…**, drag one `.md` or `.markdown` file onto the window, double-click an associated file, or pass a path:

```powershell
MDPeek.exe "C:\Documents\Project notes.markdown"
```

Paths with spaces and Unicode are supported. MDPeek normally keeps one application window: opening an associated file while it is running forwards that file to the existing window. Back and Forward reload files from disk and restore their recorded vertical positions.

The current file refreshes automatically after another application saves it. MDPeek keeps the approximate reading position and does not add refreshes to navigation history. If a replacement cannot be read, the last successfully rendered content stays visible.

### Navigation and outline

The resizable **Outline** is hidden by default and displays H1–H6 headings as a hierarchy when opened. Select a heading to navigate to it. The current section follows the reading position. The section control beside a rendered heading selects that heading through the next peer or parent heading.

### Copy formats

| Command | Result |
| --- | --- |
| Copy | Rendered plain text |
| Copy as HTML | Clean HTML with a plain-text fallback |
| Copy as Markdown | Selected content represented as Markdown |

**Copy as Markdown** (`Ctrl+Shift+M`) preserves meaningful headings, emphasis, links, lists, quotes, tables, and code. Partial selections receive balanced formatting where supported; selecting the complete document preserves the original source where possible. The code-block control copies source code without fences or highlighting markup.

### Printing

Choose **File > Print…** or press `Ctrl+P`. MDPeek prints the complete document with a print-friendly light layout through Qt's native printer selection; a text selection does not limit printing and the welcome screen is not printable.

To create a PDF on Windows:

1. Open Print with `Ctrl+P`.
2. Choose the print command in the preview.
3. Select **Microsoft Print to PDF**.
4. Choose a destination filename.

The resulting PDF uses the native Windows PDF printer; MDPeek has no separate PDF exporter.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open a Markdown file |
| `Alt+Left` | Back |
| `Alt+Right` | Forward |
| `Ctrl+C` | Copy rendered plain text |
| `Ctrl+Shift+C` | Copy as HTML |
| `Ctrl+Shift+M` | Copy as Markdown |
| `Ctrl+A` | Select all |
| `Ctrl+H` | Show or hide the document outline |
| `Ctrl+P` | Print preview |
| `F1` | Open Help |
| `Ctrl+Q` | Exit |

## Security and privacy

MDPeek does not edit Markdown files and includes no analytics or telemetry. Local documents are rendered locally with Qt; there is no browser engine, JavaScript, remote theme, or CDN. Raw HTML support is limited by Qt's Markdown renderer.

Remote images referenced by a document may be fetched over the network. Opening an untrusted document can therefore reveal your IP address to its remote image hosts. External links open in the system browser only when selected.

## Known limitations

- The first release is unsigned and may trigger a SmartScreen warning.
- Windows may require explicit confirmation to change an existing file association.
- Only Windows x64 packages are initially distributed.
- Complex table layout, image selection, and print pagination follow Qt's document-layout capabilities.

## Development

MDPeek requires Python 3.10 or newer; release automation uses Python 3.12 on Windows.

```powershell
git clone https://github.com/DiCaver/mdpeek.git
cd mdpeek
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m mdpeek examples\showcase.md
python -m pytest tests
```

On non-Windows systems, tests set Qt's offscreen platform automatically. Windows packaging uses PyInstaller one-folder mode and Inno Setup 6:

```powershell
.\scripts\build-windows.ps1
```

The script creates an isolated `.release-venv`, runs all tests before packaging, builds the application and portable ZIP, compiles the installer when Inno Setup is available, and calculates final checksums. See [Building for Windows](docs/building-windows.md) and the [release guide](docs/releasing.md).

## Release verification

Compare the published checksum with PowerShell:

```powershell
Get-FileHash .\MDPeek-0.1.0-Windows-x64-Setup.exe -Algorithm SHA256
Get-FileHash .\MDPeek-0.1.0-Windows-x64-Portable.zip -Algorithm SHA256
```

The values must match `MDPeek-0.1.0-SHA256SUMS.txt` from the same release.

## Roadmap

Near-term work is limited to code signing, feedback from the first packaged release, and carefully selected usability improvements. MDPeek will remain a Markdown viewer rather than an editor.

## License

MDPeek is free and open source under the [MIT License](LICENSE).
