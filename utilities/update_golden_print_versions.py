from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _update_archive(archive_path: Path, version: str) -> None:
    with ZipFile(archive_path) as source:
        entries = [(info, source.read(info)) for info in source.infolist()]

    updated = False
    with tempfile.NamedTemporaryFile(
        dir=archive_path.parent,
        prefix=f".{archive_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)

    try:
        with ZipFile(temporary_path, "w", ZIP_DEFLATED) as destination:
            for info, content in entries:
                if info.filename.endswith("/print_settings.json"):
                    settings = json.loads(content)
                    settings["Design"]["Slicer"] = f"PyMFCAD v{version}"
                    content = (json.dumps(settings, indent=2) + "\n").encode("utf-8")
                    updated = True
                destination.writestr(info, content)
        if not updated:
            raise ValueError(f"No print_settings.json found in {archive_path}")
        os.replace(temporary_path, archive_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1]:
        raise SystemExit("Usage: update_golden_print_versions.py VERSION")

    version = sys.argv[1]
    archives = sorted(Path("tests/golden_prints").glob("*.zip"))
    if not archives:
        raise SystemExit("No golden print archives found")
    for archive in archives:
        _update_archive(archive, version)


if __name__ == "__main__":
    main()
