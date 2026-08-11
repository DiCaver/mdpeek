# Building MDPeek for Windows

## Requirements

- 64-bit Windows 10 or 11
- Python 3.12 available through the `py` launcher
- PowerShell
- Inno Setup 6 for installer builds

From the repository root, run:

```powershell
.\scripts\build-windows.ps1
```

The script uses `.release-venv`, installs `.[release]`, and runs the complete test suite before deleting only `build`, `dist`, and `installer/output`. It then generates Windows version metadata from `mdpeek/version.py`, runs the checked-in one-folder PyInstaller spec, creates the portable ZIP, optionally compiles the installer, and hashes the final artifacts.

Use `-SkipInstaller` for a packaging smoke build when Inno Setup is unavailable. Use `-ReuseEnvironment` to avoid reinstalling an existing build environment.

Outputs are placed in `dist/artifacts`:

```text
MDPeek-0.1.0-Windows-x64-Setup.exe
MDPeek-0.1.0-Windows-x64-Portable.zip
MDPeek-0.1.0-SHA256SUMS.txt
```

The application is intentionally built in one-folder windowed mode. Qt print support, network/SSL support, image plugins, platform plugins, and Pygments lexers are included by PyInstaller's maintained hooks; the spec adds only the runtime icon.

Review `build/mdpeek/warn-mdpeek.txt` after a build. Missing optional platform-specific modules are common, but unexplained MDPeek, Qt, or Pygments imports must be resolved before release.
