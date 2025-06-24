"""
Backend module.
"""

from .color import Color
from .manifold3d import (
    set_fn,
    Shape,
    Cube,
    Cylinder,
    Sphere,
    RoundedCube,
    TextExtrusion,
    ImportModel,
    TPMS,
    _render,
    _slice_component,
)
from .polychannel import (
    PolychannelShape,
    BezierCurveShape,
    _preprocess_polychannel_shapes,
)
