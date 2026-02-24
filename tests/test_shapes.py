from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from openmfd import Component
from openmfd.backend import (
    Color,
    Cube,
    Cylinder,
    ImportModel,
    RoundedCube,
    Shape,
    Sphere,
    TextExtrusion,
    TPMS,
)
from tests.utils.mesh_metrics import compute_mesh_metrics, load_mesh


def _build_component_with_bulk(shape: Shape, *, size=(30, 30, 30)) -> Component:
    comp = Component(size=size, position=(0, 0, 0), quiet=True)
    comp.add_label("bulk", Color.from_name("blue", 255))
    comp.add_bulk("shape", shape, "bulk")
    return comp


def _render_and_validate(component: Component, out_path: Path) -> None:
    component.render(str(out_path))
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    mesh = load_mesh(out_path)
    metrics = compute_mesh_metrics(mesh)
    assert metrics["vertex_count"] > 0
    assert metrics["face_count"] > 0


def _assert_bbox(
    shape: Shape,
    *,
    expected_extent: tuple[float, float, float] | None = None,
    expected_min: tuple[float, float, float] | None = None,
    expected_center: tuple[float, float, float] | None = None,
    atol: float = 1e-3,
) -> None:
    bbox = shape._object.bounding_box()
    mins = (bbox[0], bbox[1], bbox[2])
    maxs = (bbox[3], bbox[4], bbox[5])
    extents = tuple(maxs[i] - mins[i] for i in range(3))
    centers = tuple((maxs[i] + mins[i]) / 2 for i in range(3))

    if expected_extent is not None:
        for actual, expected in zip(extents, expected_extent):
            assert actual == pytest.approx(expected, abs=atol)
    if expected_min is not None:
        for actual, expected in zip(mins, expected_min):
            assert actual == pytest.approx(expected, abs=atol)
    if expected_center is not None:
        for actual, expected in zip(centers, expected_center):
            assert actual == pytest.approx(expected, abs=atol)


@pytest.mark.mesh
@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "cube",
            "shape": lambda: Cube(size=(4, 6, 8), center=False, quiet=True),
            "extent": (4, 6, 8),
            "min": (0, 0, 0),
        },
        {
            "name": "cube_center",
            "shape": lambda: Cube(size=(4, 6, 8), center=True, quiet=True),
            "extent": (4, 6, 8),
            "center": (0, 0, 0),
        },
        {
            "name": "cube_zero",
            "shape": lambda: Cube(size=(0, 6, 8), center=False, quiet=True),
            "extent": (0.0001, 6, 8),
            "min": (0, 0, 0),
        },
        {
            "name": "cylinder_center",
            "shape": lambda: Cylinder(
                height=6, radius=2.0, center_xy=True, center_z=True, fn=12, quiet=True
            ),
            "extent": (4, 4, 6),
            "center": (0, 0, 0),
        },
        {
            "name": "cylinder_offset",
            "shape": lambda: Cylinder(
                height=6,
                bottom_r=1.5,
                top_r=1.5,
                center_xy=False,
                center_z=False,
                fn=100,
                quiet=True,
            ),
            "extent": (3, 3, 6),
            "min": (0, 0, 0),
        },
        {
            "name": "sphere_center",
            "shape": lambda: Sphere(
                size=(5, 4, 3), center=True, fn=8, quiet=True, _no_validation=True
            ),
            "extent": (5, 4, 3),
            "center": (0, 0, 0),
        },
        {
            "name": "sphere_offset",
            "shape": lambda: Sphere(size=(5, 4, 3), center=False, fn=-1, quiet=True),
            "extent": (5, 4, 3),
            "min": (0, 0, 0),
        },
        {
            "name": "rounded_cube",
            "shape": lambda: RoundedCube(
                size=(6, 6, 4),
                radius=(0, 1.0, 1.0),
                center=True,
                fn=8,
                quiet=True,
                _no_validation=True,
            ),
            "extent": (6, 6, 4),
            "center": (0, 0, 0),
        },
        {
            "name": "text_extrusion",
            "shape": lambda: TextExtrusion(
                text="AB", height=2, font="arial", font_size=12, quiet=True
            ),
            "extent": None,
            "center": None,
            "min": None,
        },
        {
            "name": "tpms",
            "shape": lambda: TPMS(
                size=(3, 3, 3),
                cells=(1, 1, 1),
                func=TPMS.gyroid,
                fill=0.0,
                refinement=4,
                quiet=True,
            ),
            "extent": (3, 3, 3),
            "min": (0, 0, 0),
        },
    ],
)
def test_shape_constructors_render(case, tmp_path):
    shape = case["shape"]()
    assert len(shape._keepouts) > 0

    if case["name"] == "text_extrusion":
        _assert_bbox(shape, expected_extent=None)
        bbox = shape._object.bounding_box()
        assert bbox[5] - bbox[2] == pytest.approx(2, abs=1e-3)
        assert bbox[5] > bbox[2]
    else:
        _assert_bbox(
            shape,
            expected_extent=case.get("extent"),
            expected_min=case.get("min"),
            expected_center=case.get("center"),
        )

    component = _build_component_with_bulk(shape)
    _render_and_validate(component, tmp_path / f"{case['name']}.glb")


@pytest.mark.mesh
def test_import_model_constructor_render(tmp_path):
    mesh = trimesh.creation.box(extents=(1.0, 2.0, 3.0))
    mesh_path = tmp_path / "box.stl"
    mesh.export(mesh_path)

    shape = ImportModel(filename=str(mesh_path), auto_repair=False, quiet=True)
    _assert_bbox(shape, expected_extent=(1.0, 2.0, 3.0), expected_center=(0, 0, 0))
    component = _build_component_with_bulk(shape)
    _render_and_validate(component, tmp_path / "ImportModel.glb")


def _bbox_min_max(shape: Shape):
    bbox = shape._object.bounding_box()
    return bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]


def test_shape_ops_add_sub_and_hull_copy():
    a = Cube(size=(6, 6, 6), center=True, quiet=True)
    b = Cube(size=(6, 6, 6), center=True, quiet=True).translate((1, 0, 0))

    add_shape = a.copy()
    add_shape + b.copy()
    assert _bbox_min_max(add_shape)[3] - _bbox_min_max(add_shape)[0] == pytest.approx(7)
    assert _bbox_min_max(add_shape)[4] - _bbox_min_max(add_shape)[1] == pytest.approx(6)
    assert _bbox_min_max(add_shape)[5] - _bbox_min_max(add_shape)[2] == pytest.approx(6)

    sub_shape = a.copy()
    sub_shape - b.copy()
    assert _bbox_min_max(sub_shape)[3] - _bbox_min_max(sub_shape)[0] == pytest.approx(1)
    assert _bbox_min_max(sub_shape)[4] - _bbox_min_max(sub_shape)[1] == pytest.approx(6)
    assert _bbox_min_max(sub_shape)[5] - _bbox_min_max(sub_shape)[2] == pytest.approx(6)

    and_shape = a.copy()
    and_shape & b.copy()
    assert _bbox_min_max(and_shape)[3] - _bbox_min_max(and_shape)[0] == pytest.approx(5)
    assert _bbox_min_max(and_shape)[4] - _bbox_min_max(and_shape)[1] == pytest.approx(6)
    assert _bbox_min_max(and_shape)[5] - _bbox_min_max(and_shape)[2] == pytest.approx(6)

    hull_shape = a.copy()
    hull_shape.hull(b.copy())
    assert _bbox_min_max(hull_shape)[3] - _bbox_min_max(hull_shape)[0] == pytest.approx(7)
    assert _bbox_min_max(hull_shape)[4] - _bbox_min_max(hull_shape)[1] == pytest.approx(6)
    assert _bbox_min_max(hull_shape)[5] - _bbox_min_max(hull_shape)[2] == pytest.approx(6)

    c = a.copy()
    assert c is not a
    assert _bbox_min_max(c) == _bbox_min_max(a)


def test_shape_ops_translate_rotate_mirror_resize():
    shape = Cube(size=(4, 6, 8), center=False, quiet=True)
    min_x, min_y, min_z, max_x, max_y, max_z = _bbox_min_max(shape)

    shape.translate((2, 3, 4))
    t_min_x, t_min_y, t_min_z, t_max_x, t_max_y, t_max_z = _bbox_min_max(shape)
    assert t_min_x == pytest.approx(min_x + 2)
    assert t_min_y == pytest.approx(min_y + 3)
    assert t_min_z == pytest.approx(min_z + 4)
    assert t_max_x == pytest.approx(max_x + 2)
    assert t_max_y == pytest.approx(max_y + 3)
    assert t_max_z == pytest.approx(max_z + 4)

    shape.rotate((0, 0, 90))
    r_min_x, r_min_y, _, r_max_x, r_max_y, _ = _bbox_min_max(shape)
    assert r_max_x - r_min_x == pytest.approx(t_max_y - t_min_y)
    assert r_max_y - r_min_y == pytest.approx(t_max_x - t_min_x)

    shape.mirror((True, False, False))
    m_min_x, _, _, m_max_x, _, _ = _bbox_min_max(shape)
    assert m_min_x == pytest.approx(-r_max_x)
    assert m_max_x == pytest.approx(-r_min_x)

    shape.resize((10, 12, 14))
    s_min_x, s_min_y, s_min_z, s_max_x, s_max_y, s_max_z = _bbox_min_max(shape)
    assert s_max_x - s_min_x == pytest.approx(10)
    assert s_max_y - s_min_y == pytest.approx(12)
    assert s_max_z - s_min_z == pytest.approx(14)
