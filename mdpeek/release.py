"""Testable release naming and Windows metadata helpers."""

from __future__ import annotations

from pathlib import Path

from .version import __version__

PRODUCT_NAME = "MDPeek"
PUBLISHER = "MDPeek contributors"


def normalize_tag(tag: str) -> str:
    return tag.removeprefix("v")


def validate_tag(tag: str, version: str = __version__) -> None:
    if normalize_tag(tag) != version:
        raise ValueError(f"tag {tag!r} does not match application version {version!r}")


def artifact_names(version: str = __version__) -> dict[str, str]:
    prefix = f"MDPeek-{version}-Windows-x64"
    return {
        "installer": f"{prefix}-Setup.exe",
        "portable": f"{prefix}-Portable.zip",
        "checksums": f"MDPeek-{version}-SHA256SUMS.txt",
    }


def windows_version(version: str = __version__) -> tuple[int, int, int, int]:
    parts = tuple(int(part) for part in version.split("."))
    if len(parts) != 3:
        raise ValueError("MDPeek versions must contain three numeric components")
    return (*parts, 0)


def version_info_text(version: str = __version__) -> str:
    four = windows_version(version)
    comma_version = ", ".join(map(str, four))
    dotted_version = ".".join(map(str, four))
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({comma_version}), prodvers=({comma_version}), mask=0x3f,
    flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', '{PUBLISHER}'),
    StringStruct('FileDescription', 'MDPeek Markdown Viewer'),
    StringStruct('FileVersion', '{dotted_version}'),
    StringStruct('InternalName', 'MDPeek'),
    StringStruct('LegalCopyright', 'Copyright (c) MDPeek contributors'),
    StringStruct('OriginalFilename', 'MDPeek.exe'),
    StringStruct('ProductName', '{PRODUCT_NAME}'),
    StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])
"""


def write_version_info(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version_info_text(), encoding="utf-8")
