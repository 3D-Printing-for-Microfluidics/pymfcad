from __future__ import annotations

import importlib.util
import runpy
import zipfile
from pathlib import Path

import pytest

from tests.utils.golden_compare import compare_directories


_INTEGRATION_CASES = [
    {
        "name": "full_test",
        "script": "examples/full_test.py",
        "zip": "tests/golden_prints/full_test.zip",
        "print_dir": "full_test_demo",
    },
    {
        "name": "embedded_device_test",
        "script": "examples/embedded_device_test.py",
        "zip": "tests/golden_prints/embedded_device_test.zip",
        "print_dir": "embedded_device_demo",
    },
    {
        "name": "special_techniques_test",
        "script": "examples/special_techniques_test.py",
        "zip": "tests/golden_prints/special_techniques_test.zip",
        "print_dir": "special_techniques_demo",
    },
    {
        "name": "stitched_device_test",
        "script": "examples/stitched_device_test.py",
        "zip": "tests/golden_prints/stitched_device_test.zip",
        "print_dir": "stitched_demo",
    },
]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("case", _INTEGRATION_CASES, ids=[c["name"] for c in _INTEGRATION_CASES])
def test_example_outputs_match_golden(case, tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / case["script"]
    golden_zip = repo_root / case["zip"]

    if not script_path.exists():
        pytest.skip(f"{case['script']} not available")
    if not golden_zip.exists():
        pytest.skip(f"Golden zip not available for {case['name']}")

    golden_extract_dir = tmp_path / f"golden_{case['name']}"
    with zipfile.ZipFile(golden_zip, "r") as archive:
        archive.extractall(golden_extract_dir)

    top_level_dirs = {
        p.relative_to(golden_extract_dir).parts[0]
        for p in golden_extract_dir.rglob("*")
        if p.is_dir() and p.relative_to(golden_extract_dir).parts
    }

    def _find_dir(candidates: list[str]) -> Path | None:
        for name in candidates:
            if name in top_level_dirs:
                return golden_extract_dir / name
        return None

    golden_mesh_dir = _find_dir(["visualization", "_visualization"])
    golden_print_dir = _find_dir(["printfile", case["print_dir"]])

    if golden_mesh_dir is None or golden_print_dir is None:
        pytest.skip("Golden integration folders missing in zip")

    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(script_path), run_name="__main__")

    generated_mesh_dir = tmp_path / "_visualization"
    generated_print_dir = tmp_path / case["print_dir"]

    compare_directories(generated_mesh_dir, golden_mesh_dir, ignore_extra_generated=True)
    compare_directories(generated_print_dir, golden_print_dir, ignore_extra_generated=True)
