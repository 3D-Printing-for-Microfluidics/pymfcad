from __future__ import annotations

import numpy as np
import pytest

from pymfcad import BezierCurveShape, Polychannel, PolychannelShape


def _shape(
    position: tuple[int, int, int],
    *,
    size: tuple[int, int, int] = (2, 2, 2),
    corner_radius: float | None = None,
    corner_segments: int | None = None,
) -> PolychannelShape:
    return PolychannelShape(
        "cube",
        position=position,
        size=size,
        absolute_position=True,
        corner_radius=corner_radius,
        corner_segments=corner_segments,
    )


def test_polychannel_shape_equality():
    shape1 = PolychannelShape("cube", position=np.array([0, 0, 0]), size=(2, 2, 2))
    shape2 = PolychannelShape("cube", position=np.array([0, 0, 0]), size=(2, 2, 2))
    shape3 = PolychannelShape("cube", position=np.array([1, 0, 0]), size=(2, 2, 2))
    assert shape1 == shape2
    assert shape1 != shape3

    bezier1 = BezierCurveShape(
        control_points=[(0, 0, 0)], bezier_segments=3, position=np.array([10, 0, 0])
    )
    bezier2 = BezierCurveShape(
        control_points=[(0, 0, 0)], bezier_segments=3, position=np.array([10, 0, 0])
    )
    bezier3 = BezierCurveShape(
        control_points=[(1, 0, 0)], bezier_segments=3, position=np.array([10, 0, 0])
    )
    assert bezier1 == bezier2
    assert bezier1 != bezier3


def test_polychannel_requires_two_shapes():
    shape = _shape((0, 0, 0))
    with pytest.raises(ValueError, match="Polychannel requires at least 2 shapes"):
        Polychannel([shape])


def test_polychannel_first_shape_requires_type_size():
    bad = PolychannelShape()
    with pytest.raises(
        ValueError, match="Shape type must be specified for the first shape"
    ):
        Polychannel([bad, _shape((0, 0, 0))])

    with pytest.raises(
        ValueError, match="Size must be specified for the first shape in a polychannel"
    ):
        bad._shape_type = "cube"
        Polychannel([bad, _shape((0, 0, 0))])


def test_polychannel_first_rounded_cube_must_have_corner_radius():
    with pytest.raises(
        ValueError,
        match="Rounded cube radius must be specified for the first round cube shape in a polychannel",
    ):
        shape = _shape((0, 0, 0))
        shape._shape_type = "rounded_cube"
        Polychannel([shape])


def test_polychannel_bezier_cannot_be_first():
    bezier = BezierCurveShape(
        shape_type="cube", size=(2, 2, 2), control_points=[(0, 0, 0)], bezier_segments=3
    )
    with pytest.raises(ValueError, match="Bezier curve cannot be the first shape"):
        Polychannel([bezier, _shape((2, 0, 0))])


def test_bezier_curve_shape_requires_control_points():
    with pytest.raises(
        ValueError, match="Bezier curve requires at least 1 control points"
    ):
        bezier = BezierCurveShape(
            shape_type="cube", size=(2, 2, 2), bezier_segments=3, control_points=None
        )
        Polychannel([_shape((0, 0, 0)), bezier])


def test_bezier_curve_shape_requires_bezier_segments():
    with pytest.raises(ValueError, match="Bezier curve requires at least 2 segments"):
        bezier = BezierCurveShape(
            shape_type="cube",
            size=(2, 2, 2),
            control_points=[(0, 0, 0)],
            bezier_segments=1,
        )
        Polychannel([_shape((0, 0, 0)), bezier])


def test_polychannel_corner_radius_not_allowed_on_first_or_last():
    shapes = [
        _shape((0, 0, 0), corner_radius=1, corner_segments=5),
        _shape((5, 0, 0), corner_radius=1, corner_segments=5),
        _shape((10, 0, 0)),
    ]
    # Should create polychannel successfully, skipping corner radius on first shape
    channel = Polychannel(shapes)
    bbox = channel._object.bounding_box()
    extents = (bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2])
    assert extents[0] > 0
    assert extents[1] > 0
    assert extents[2] > 0


def test_polychannel_corner_radius_too_large():
    shapes = [
        _shape((0, 0, 0)),
        _shape((1, 0, 0), corner_radius=5, corner_segments=5),
        _shape((1, 1, 0), corner_radius=0),
    ]
    # Should create polychannel successfully, skipping the oversized corner radius
    channel = Polychannel(shapes)
    bbox = channel._object.bounding_box()
    extents = (bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2])
    assert extents[0] > 0
    assert extents[1] > 0
    assert extents[2] > 0


def test_polychannel_corner_radius_straight_segment():
    shapes = [
        _shape((0, 0, 0)),
        _shape((5, 0, 0), corner_radius=1, corner_segments=5),
        _shape((10, 0, 0), corner_radius=0),
    ]
    Polychannel(shapes)


def test_polychannel_builds_with_rounded_corner():
    shapes = [
        _shape((0, 0, 0)),
        _shape((10, 0, 0), corner_radius=2, corner_segments=5),
        _shape((10, 10, 0), corner_radius=0),
    ]
    channel = Polychannel(shapes)
    bbox = channel._object.bounding_box()
    extents = (bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2])
    assert extents[0] > 0
    assert extents[1] > 0
    assert extents[2] > 0


def test_polychannel_builds_with_bezier_segment():
    shapes = [
        _shape((0, 0, 0)),
        BezierCurveShape(
            control_points=[(5, 0, 0)],
            bezier_segments=3,
            position=(10, 0, 0),
        ),
    ]
    channel = Polychannel(shapes)
    bbox = channel._object.bounding_box()
    extents = (bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2])
    assert extents[0] > 0
    assert extents[1] > 0
    assert extents[2] > 0


def test_polychannel_with_all_shape_types():
    shape1 = _shape((0, 0, 0))
    shape1._shape_type = "cube"
    shape2 = _shape((10, 0, 0))
    shape2._shape_type = "rounded_cube"
    shape3 = _shape((5, 0, 0))
    shape3._shape_type = "sphere"

    bezier = BezierCurveShape(
        control_points=[(15, 0, 0)],
        bezier_segments=3,
        shape_type="cube",
        position=np.array([20, 0, 0]),
    )

    channel = Polychannel([shape1, shape2, shape3, bezier])


def test_polychannel_show_only_shapes():
    shape1 = _shape((0, 0, 0))
    shape1._shape_type = "sphere"
    shape2 = _shape(None)
    shape2._shape_type = "rounded_cube"
    shape3 = _shape((5, 0, 0))
    shape3._shape_type = "cube"

    bezier = BezierCurveShape(
        control_points=[(15, 0, 0)],
        bezier_segments=3,
        shape_type="sphere",
        position=np.array([20, 0, 0]),
    )

    channel = Polychannel([shape1, shape2, shape3, bezier], show_only_shapes=True)
