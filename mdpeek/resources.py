"""Resolve application resources in source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str | Path) -> Path:
    """Return a resource path without depending on the working directory."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    root = Path(bundle_root) if bundle_root else Path(__file__).resolve().parent.parent
    return root / Path(relative_path)


def application_icon_path() -> Path | None:
    """Return the runtime icon when present; absence is non-fatal."""
    path = resource_path(Path("assets") / "mdpeek.ico")
    return path if path.is_file() else None
