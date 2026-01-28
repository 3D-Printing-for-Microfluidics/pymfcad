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

from .slice import slice_component, rle_decode_packed, rle_encode_packed, rle_is_all_non_zeros, rle_is_all_zeros
from .polychannel import (
    Polychannel,
    PolychannelShape,
    BezierCurveShape,
)
