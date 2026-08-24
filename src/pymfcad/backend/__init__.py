"""
Module that provides 3D manifold shapes and transforms as well as polychannel (complex hulled shapes).
"""

from .color import Color
from .manifold3d import (
    TPMS,
    Cube,
    Cylinder,
    ImportModel,
    RoundedCube,
    Shape,
    Sphere,
    TextExtrusion,
    TPMSGrid,
    set_fn,
)
from .polychannel import (
    BezierCurveShape,
    Polychannel,
    PolychannelShape,
)
from .render import render_component
from .slice import (
    rle_decode_packed,
    rle_encode_packed,
    rle_is_all_non_zeros,
    rle_is_all_zeros,
    slice_component,
)
