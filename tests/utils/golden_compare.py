from __future__ import annotations

import difflib
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from tests.utils.mesh_metrics import (
    assert_mesh_metrics_close,
    compute_mesh_metrics,
    load_mesh,
)


def _iter_files(base_dir: Path) -> list[Path]:
    return sorted(
        [p for p in base_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    )


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _strip_json_dates(value):
    if isinstance(value, dict):
        return {
            key: _strip_json_dates(val)
            for key, val in value.items()
            if key.lower() not in {"date", "design file"}
        }
    if isinstance(value, list):
        return [_strip_json_dates(item) for item in value]
    return value


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return _strip_json_dates(data)


def _json_diff(expected, actual) -> str:
    expected_text = json.dumps(expected, indent=2, sort_keys=True)
    actual_text = json.dumps(actual, indent=2, sort_keys=True)
    diff = difflib.unified_diff(
        expected_text.splitlines(),
        actual_text.splitlines(),
        fromfile="golden",
        tofile="generated",
        lineterm="",
    )
    return "\n".join(diff)


def compare_directories(
    generated_dir: Path,
    golden_dir: Path,
    *,
    json_extensions: Iterable[str] = (".json",),
    mesh_extensions: Iterable[str] = (".glb", ".stl", ".obj"),
    ignore_extra_generated: bool = True,
) -> None:
    if not generated_dir.exists():
        raise AssertionError(f"Generated directory missing: {generated_dir}")
    if not golden_dir.exists():
        raise AssertionError(f"Golden directory missing: {golden_dir}")

    generated_files = _iter_files(generated_dir)
    golden_files = _iter_files(golden_dir)

    generated_rel = {p.relative_to(generated_dir) for p in generated_files}
    golden_rel = {p.relative_to(golden_dir) for p in golden_files}

    missing = sorted(golden_rel - generated_rel)
    if missing:
        raise AssertionError(f"Missing golden files: {missing[:10]}")

    if not ignore_extra_generated:
        extra = sorted(generated_rel - golden_rel)
        if extra:
            raise AssertionError(f"Extra generated files: {extra[:10]}")

    json_exts = {ext.lower() for ext in json_extensions}
    mesh_exts = {ext.lower() for ext in mesh_extensions}

    for rel_path in sorted(golden_rel):
        gen_path = generated_dir / rel_path
        gold_path = golden_dir / rel_path
        suffix = gen_path.suffix.lower()

        if suffix in json_exts:
            gen_json = _load_json(gen_path)
            gold_json = _load_json(gold_path)
            if gen_json != gold_json:
                diff = _json_diff(gold_json, gen_json)
                raise AssertionError(f"JSON mismatch: {rel_path}\n{diff}")
        elif suffix in mesh_exts:
            gen_mesh = load_mesh(gen_path)
            gold_mesh = load_mesh(gold_path)
            if gen_mesh.is_empty or gold_mesh.is_empty:
                if gen_mesh.is_empty != gold_mesh.is_empty:
                    raise AssertionError(f"Empty mesh mismatch: {rel_path}")
                continue
            gen_metrics = compute_mesh_metrics(gen_mesh)
            gold_metrics = compute_mesh_metrics(gold_mesh)
            assert_mesh_metrics_close(gen_metrics, gold_metrics)
        else:
            if _sha256(gen_path) != _sha256(gold_path):
                raise AssertionError(f"File mismatch: {rel_path}")
