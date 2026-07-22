from __future__ import annotations

from pathlib import Path

import pytest

from pymfcad import Component, Port
from pymfcad.backend import Color, Cube, Shape
from tests.utils.mesh_metrics import compute_mesh_metrics, load_mesh


def _build_parent_component(size=(40, 30, 20)) -> Component:
    comp = Component(size=size, position=(0, 0, 0), quiet=True)
    comp.add_label("device", Color.from_name("gray", 255))
    comp.add_label("fluidic", Color.from_name("blue", 255))
    comp.add_bulk("device_bulk", Cube(size=size, center=False), label="device")
    return comp


def _preview_and_validate(component: Component, preview_dir: Path, expected_files: list[str]) -> None:
    component.preview(preview_dir=str(preview_dir))
    for filename in expected_files:
        path = preview_dir / filename
        assert path.exists()
        assert path.stat().st_size > 0

    mesh_file = next(
        (name for name in expected_files if not name.startswith("bounding_box")),
        expected_files[0],
    )
    mesh = load_mesh(preview_dir / mesh_file)
    metrics = compute_mesh_metrics(mesh)
    assert metrics["vertex_count"] > 0
    assert metrics["face_count"] > 0


def _bbox_min_max(shape: Shape):
    bbox = shape._object.bounding_box()
    return bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5]


@pytest.mark.mesh
def test_subcomponent_preview_outputs_and_labels(tmp_path):
    parent = _build_parent_component()

    child = Component(size=(12, 10, 8), position=(5, 4, 3), quiet=True)
    child.add_label("device", Color.from_name("green", 255))
    child.add_label("fluidic", Color.from_name("red", 255))
    child.add_bulk("child_bulk", Cube(size=(12, 10, 8), center=False), label="device")
    child.add_void(
        "channel",
        Cube(size=(4, 4, 4), center=False).translate((2, 2, 2)),
        label="fluidic",
    )
    child.add_port(
        "P1",
        Port(
            Port.PortType.IN,
            position=(0, 4, 2),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.NEG_X,
        ),
    )

    child.add_port(
        "P2",
        Port(
            Port.PortType.INOUT,
            position=(0, 4, 2),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.NEG_X,
        ),
    )

    child.add_port(
        "P3",
        Port(
            Port.PortType.INOUT,
            position=(0, 4, 2),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.NEG_X,
        ),
    )



    parent.add_subcomponent("child", child, subtract_bounding_box=False)

    assert "child.device" in child.labels
    assert "child.fluidic" in child.labels
    assert child.bulk_shapes["child_bulk"]._label == "child.device"
    assert child.shapes["channel"]._label == "child.fluidic"

    preview_dir = tmp_path / "preview"
    _preview_and_validate(
        parent,
        preview_dir,
        [
            "bounding_box.glb",
            "bulk_device.glb",
            "bulk_child.device.glb",
            "void_child.fluidic.glb",
        ],
    )


@pytest.mark.mesh
def test_subcomponent_translation_applied_and_locking():
    parent = _build_parent_component(size=(30, 30, 30))

    child = Component(size=(10, 8, 6), position=(0, 0, 0), quiet=True)
    child.add_label("device", Color.from_name("green", 255))
    child.add_bulk("child_bulk", Cube(size=(10, 8, 6), center=False), label="device")
    child.translate((5, 4, 3))

    parent.add_subcomponent("child", child, subtract_bounding_box=False)

    min_x, min_y, min_z, max_x, max_y, max_z = _bbox_min_max(child.bulk_shapes["child_bulk"])
    assert min_x == pytest.approx(5)
    assert min_y == pytest.approx(4)
    assert min_z == pytest.approx(3)
    assert max_x == pytest.approx(15)
    assert max_y == pytest.approx(12)
    assert max_z == pytest.approx(9)

    with pytest.raises(ValueError):
        child.add_port(
            "P2",
            Port(
                Port.PortType.IN,
                position=(0, 0, 0),
                size=(2, 2, 2),
                surface_normal=Port.SurfaceNormal.NEG_X,
            ),
        )


@pytest.mark.mesh
def test_component_ops_translate_rotate_mirror():
    parent = _build_parent_component(size=(50, 50, 50))

    child = Component(size=(10, 8, 6), position=(5, 4, 3), quiet=True)
    child.add_label("device", Color.from_name("green", 255))
    child.add_bulk("child_bulk", Cube(size=(10, 8, 6), center=False), label="device")
    child.add_port(
        "P1",
        Port(
            Port.PortType.IN,
            position=(1, 2, 1),
            size=(2, 2, 2),
            surface_normal=Port.SurfaceNormal.POS_X,
        ),
    )

    child1 = child.copy()

    child1.translate((2, 3, 4))
    child2 = child1.copy()
    parent.add_subcomponent("child1", child1, subtract_bounding_box=False)
    bbox = child1.get_bounding_box()
    bbox = tuple(int(x) for x in bbox)
    assert bbox == (7, 7, 7, 17, 15, 13)

    child2.rotate(90, in_place=True).translate((10,10,10))
    child3 = child2.copy()
    parent.add_subcomponent("child2", child2, subtract_bounding_box=False)
    bbox = child2.get_bounding_box()
    bbox = tuple(int(x) for x in bbox)
    assert bbox == (17, 17, 17, 25, 27, 23)

    child3.mirror(mirror_x=True, mirror_y=False, in_place=True).translate((10,10,10))
    parent.add_subcomponent("child3", child3, subtract_bounding_box=False)
    bbox = child3.get_bounding_box()
    bbox = tuple(int(x) for x in bbox)
    assert bbox == (27, 27, 27, 35, 37, 33)


def test_component_no_bulk():
    comp = Component(size=(10, 10, 10), position=(0, 0, 0), quiet=True)
    comp.add_label("device", Color.from_name("gray", 255))
    comp.add_port(
        "P1",
        Port(
            Port.PortType.IN,
            position=(1, 2, 3),
            size=(2, 2, 2),
            surface_normal=Port.SurfaceNormal.POS_X,
        ),
    )

    with pytest.raises(ValueError, match="no bulk shapes to render."):
        comp.render()