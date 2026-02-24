import trimesh

from tests.utils.mesh_metrics import (
    assert_mesh_metrics_close,
    compute_mesh_metrics,
    load_mesh,
    load_metrics_json,
)


def test_compute_mesh_metrics_matches_golden():
    expected = load_metrics_json("tests/golden_meshes/box_metrics.json")
    mesh = trimesh.creation.box(extents=(1.0, 2.0, 3.0))
    actual = compute_mesh_metrics(mesh)
    assert_mesh_metrics_close(actual, expected)


def test_mesh_roundtrip_file_metrics(tmp_path):
    expected = load_metrics_json("tests/golden_meshes/box_metrics.json")
    mesh = trimesh.creation.box(extents=(1.0, 2.0, 3.0))
    mesh_path = tmp_path / "box.stl"
    mesh.export(mesh_path)

    loaded = load_mesh(mesh_path)
    actual = compute_mesh_metrics(loaded)
    assert_mesh_metrics_close(actual, expected)
