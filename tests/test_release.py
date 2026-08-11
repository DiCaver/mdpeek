import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

if sys.platform != "win32":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image

from mdpeek.app import startup_path_error
from mdpeek.release import artifact_names, normalize_tag, validate_tag, version_info_text
from mdpeek.resources import application_icon_path, resource_path
from mdpeek.version import __version__


ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_authoritative_version_and_names(self) -> None:
        self.assertEqual(__version__, "0.1.0")
        self.assertEqual(normalize_tag("v0.1.0"), "0.1.0")
        validate_tag("v0.1.0")
        with self.assertRaises(ValueError):
            validate_tag("v0.2.0")
        self.assertEqual(artifact_names(), {
            "installer": "MDPeek-0.1.0-Windows-x64-Setup.exe",
            "portable": "MDPeek-0.1.0-Windows-x64-Portable.zip",
            "checksums": "MDPeek-0.1.0-SHA256SUMS.txt",
        })

    def test_windows_metadata_uses_release_identity(self) -> None:
        metadata = version_info_text()
        for expected in (
            "MDPeek Markdown Viewer", "MDPeek contributors", "0.1.0.0",
            "0, 1, 0, 0", "MDPeek.exe", "ProductVersion', '0.1.0",
        ):
            self.assertIn(expected, metadata)

    def test_source_resource_resolution_ignores_working_directory(self) -> None:
        expected = ROOT / "assets" / "mdpeek.ico"
        old_cwd = Path.cwd()
        os.chdir(ROOT / "examples")
        try:
            self.assertEqual(resource_path("assets/mdpeek.ico"), expected)
            self.assertEqual(application_icon_path(), expected)
        finally:
            os.chdir(old_cwd)

    def test_simulated_pyinstaller_and_missing_icon(self) -> None:
        bundle = ROOT / ".tmp" / "simulated-bundle"
        icon = bundle / "assets" / "mdpeek.ico"
        icon.parent.mkdir(parents=True, exist_ok=True)
        try:
            icon.write_bytes(b"icon")
            with patch.object(sys, "_MEIPASS", str(bundle), create=True):
                self.assertEqual(application_icon_path(), icon)
            icon.unlink()
            with patch.object(sys, "_MEIPASS", str(bundle), create=True):
                self.assertIsNone(application_icon_path())
        finally:
            icon.unlink(missing_ok=True)

    def test_icon_contains_required_windows_sizes(self) -> None:
        image = Image.open(ROOT / "assets" / "mdpeek.ico")
        sizes = image.info["sizes"]
        for size in (16, 20, 24, 32, 48, 64, 128, 256):
            self.assertIn((size, size), sizes)

    def test_command_line_target_validation(self) -> None:
        root = ROOT / "tests" / "fixtures" / "release paths"
        root.mkdir(exist_ok=True)
        try:
            valid = root / "notes with spaces č.markdown"
            valid.write_text("# valid", encoding="utf-8")
            unsupported = root / "notes.txt"
            unsupported.write_text("text", encoding="utf-8")
            self.assertIsNone(startup_path_error(valid))
            self.assertIn(".md", startup_path_error(unsupported) or "")
            self.assertIn("directory", startup_path_error(root) or "")
            self.assertIn("does not exist", startup_path_error(root / "missing.md") or "")
        finally:
            for path in root.iterdir():
                path.unlink()
            root.rmdir()

    def test_packaging_files_have_release_safety_properties(self) -> None:
        spec = (ROOT / "packaging" / "mdpeek.spec").read_text(encoding="utf-8")
        installer = (ROOT / "installer" / "MDPeek.iss").read_text(encoding="utf-8")
        self.assertIn('console=False', spec)
        self.assertIn('name="MDPeek"', spec)
        self.assertIn('assets" / "mdpeek.ico', spec)
        self.assertIn("PrivilegesRequired=lowest", installer)
        self.assertIn('""%1""', installer)
        self.assertIn(".md\\OpenWithProgids", installer)
        self.assertIn(".markdown\\OpenWithProgids", installer)
        self.assertIn("CompareText(Existing, '{#AppProgID}')", installer)
        self.assertIn("UserChoice", installer)
        self.assertIn("RegQueryStringValue(HKCR, Extension", installer)


if __name__ == "__main__":
    unittest.main()
