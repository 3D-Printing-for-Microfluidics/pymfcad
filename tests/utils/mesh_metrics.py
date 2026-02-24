from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import trimesh


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    """Load a mesh from disk."""
    return trimesh.load(Path(path), force="mesh")


def compute_mesh_metrics(mesh: trimesh.Trimesh, decimals: int = 6) -> Dict[str, Any]:
    """Compute mesh metrics for regression testing."""
    bounds = np.round(mesh.bounds, decimals=decimals).tolist()
    return {
        "vertex_count": int(mesh.vertices.shape[0]),
        "face_count": int(mesh.faces.shape[0]),
        "bounds": bounds,
        "volume": float(np.round(mesh.volume, decimals=decimals)),
        "area": float(np.round(mesh.area, decimals=decimals)),
        "is_watertight": bool(mesh.is_watertight),
        "euler_number": int(mesh.euler_number),
    }


def load_metrics_json(path: str | Path) -> Dict[str, Any]:
    """Load golden mesh metrics from JSON."""
    return json.loads(Path(path).read_text())


def assert_mesh_metrics_close(
    actual: Dict[str, Any],
    expected: Dict[str, Any],
    *,
    atol: float = 1e-6,
    rtol: float = 1e-6,
) -> None:
    """Assert metric dictionaries match within tolerance."""
    for key, expected_value in expected.items():
        if key not in actual:
            raise AssertionError(f"Missing key in actual metrics: {key}")

        actual_value = actual[key]

        if isinstance(expected_value, (int, float)):
            if not np.isclose(actual_value, expected_value, atol=atol, rtol=rtol):
                raise AssertionError(
                    f"Metric '{key}' mismatch: actual={actual_value}, expected={expected_value}"
                )
        elif isinstance(expected_value, list):
            if not np.allclose(
                np.array(actual_value),
                np.array(expected_value),
                atol=atol,
                rtol=rtol,
            ):
                raise AssertionError(
                    f"Metric '{key}' mismatch: actual={actual_value}, expected={expected_value}"
                )
        else:
            if actual_value != expected_value:
                raise AssertionError(
                    f"Metric '{key}' mismatch: actual={actual_value}, expected={expected_value}"
                )
