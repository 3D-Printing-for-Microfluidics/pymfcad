"""
Module that provides 3D manifold shapes and transforms as well as polychannel (complex hulled shapes).
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
)
from .render import render_component

from .slice import slice_component
from .polychannel import (
    Polychannel,
    PolychannelShape,
    BezierCurveShape,
)
