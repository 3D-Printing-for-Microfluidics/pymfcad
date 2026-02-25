from __future__ import annotations

from pathlib import Path

import pytest

from openmfd import Component, Port, Router
from openmfd.backend import Color, Cube
from openmfd import PolychannelShape, BezierCurveShape
from tests.utils.mesh_metrics import compute_mesh_metrics, load_mesh


def _render_and_validate(component: Component, out_path: Path) -> None:
    component.render(str(out_path))
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    mesh = load_mesh(out_path)
    metrics = compute_mesh_metrics(mesh)
    assert metrics["vertex_count"] > 0
    assert metrics["face_count"] > 0


def _build_parent_component(size=(40, 30, 20)) -> Component:
    comp = Component(size=size, position=(0, 0, 0), quiet=True)
    comp.add_label("device", Color.from_name("gray", 255))
    comp.add_label("fluidic", Color.from_name("blue", 255))
    comp.add_bulk("device_bulk", Cube(size=size, center=False), label="device")
    return comp


@pytest.mark.mesh
def test_routing_fractional_path_render(tmp_path):
    comp = _build_parent_component()

    comp.add_port(
        "IN",
        Port(
            Port.PortType.IN,
            position=(0, 12, 8),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.NEG_X,
        ),
    )
    comp.add_port(
        "OUT",
        Port(
            Port.PortType.OUT,
            position=(40, 12, 8),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.POS_X,
        ),
    )

    router = Router(comp, channel_size=(4, 4, 4), channel_margin=(2, 2, 2), quiet=True)
    router.route_with_fractional_path(comp.IN, comp.OUT, [(1, 1, 1)], label="fluidic")
    router.finalize_routes()

    route_name = f"{comp.IN.get_name()}__to__{comp.OUT.get_name()}"
    assert route_name in comp.shapes

    _render_and_validate(comp, tmp_path / "routing_fractional.glb")


@pytest.mark.mesh
def test_routing_polychannel_render(tmp_path):
    comp = _build_parent_component()

    comp.add_port(
        "IN",
        Port(
            Port.PortType.IN,
            position=(0, 8, 6),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.NEG_X,
        ),
    )
    comp.add_port(
        "OUT",
        Port(
            Port.PortType.OUT,
            position=(40, 18, 6),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.POS_X,
        ),
    )

    polychannel_shapes = [
        PolychannelShape(
            "cube",
            position=(20, 8, 6),
            size=(4, 4, 4),
            absolute_position=True,
        ),
        PolychannelShape(
            "cube",
            position=(20, 18, 6),
            size=(4, 4, 4),
            absolute_position=True,
        ),
    ]

    router = Router(comp, channel_size=(4, 4, 4), channel_margin=(2, 2, 2), quiet=True)
    router.route_with_polychannel(comp.IN, comp.OUT, polychannel_shapes, label="fluidic")
    router.finalize_routes()

    route_name = f"{comp.IN.get_name()}__to__{comp.OUT.get_name()}"
    assert route_name in comp.shapes

    _render_and_validate(comp, tmp_path / "routing_polychannel.glb")


@pytest.mark.mesh
def test_routing_autoroute_render(tmp_path):
    comp = _build_parent_component(size=(60, 40, 20))

    comp.add_port(
        "IN",
        Port(
            Port.PortType.IN,
            position=(0, 10, 6),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.NEG_X,
        ),
    )
    comp.add_port(
        "OUT",
        Port(
            Port.PortType.OUT,
            position=(60, 30, 6),
            size=(4, 4, 4),
            surface_normal=Port.SurfaceNormal.POS_X,
        ),
    )

    router = Router(comp, channel_size=(4, 4, 4), channel_margin=(2, 2, 2), quiet=True)
    router.autoroute_channel(
        comp.IN,
        comp.OUT,
        label="fluidic",
        timeout=20,
        heuristic_weight=8,
        turn_weight=2,
        direction_preference=("X", "Y", "Z"),
    )
    router.finalize_routes()

    route_name = f"{comp.IN.get_name()}__to__{comp.OUT.get_name()}"
    assert route_name in comp.shapes

    _render_and_validate(comp, tmp_path / "routing_autoroute.glb")


def test_polychannel():
    shape = PolychannelShape(
        "cube",
        position=(20, 8, 6),
        size=(4, 4, 4),
        absolute_position=True,
    )
    assert shape != "not_a_shape"
    assert shape == shape

    bad_shape = PolychannelShape(
        "cube",
        position=("20", False, []),
        size=(4, 4, 4),
        absolute_position=True,
    )
    assert shape != bad_shape

    bezier_shape = BezierCurveShape(
        control_points=[(0,0,0)],
        bezier_segments=5,
    )
    assert bezier_shape != "not_a_shape"
    assert bezier_shape == bezier_shape

    bad_bezier_shape = BezierCurveShape(
        control_points=[("20",False,[])],
        bezier_segments=5,
    )
    assert bezier_shape != bad_bezier_shape

    
    