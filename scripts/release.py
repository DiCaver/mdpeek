"""Small command-line helpers used by local and CI release builds."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mdpeek.release import artifact_names, validate_tag, write_version_info  # noqa: E402
from mdpeek.version import __version__  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--validate-tag")
    parser.add_argument("--write-version-info", type=Path)
    parser.add_argument("--artifact", choices=("installer", "portable", "checksums"))
    args = parser.parse_args()
    try:
        if args.validate_tag:
            validate_tag(args.validate_tag)
        if args.write_version_info:
            write_version_info(args.write_version_info)
        if args.artifact:
            print(artifact_names()[args.artifact])
        elif args.version:
            print(__version__)
    except ValueError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
