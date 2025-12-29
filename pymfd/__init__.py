"""
This Python package provides a set of tools for designing 3D-printed microfluidic devices.

It adopts a component-based design approach, enabling easy reuse and composition of parts. The package
includes a variety of tools for routing connections between components, including fully automatic routing.

To make the most of high-resolution 3D printers, the design operates using pixels and layers as the
base units. The package supports the creation of a wide range of shapes, components, and devices, as well
as tools for rendering and slicing—slicing support is currently limited to our custom 3D printers.

Advanced structures such as polychannels (complex hulled shapes) and Bézier curves are also supported, making it suitable for
complex microfluidic architectures.
"""

from .pymfd import (
    Port,
    Component,
    VariableLayerThicknessComponent,
    Device,
    Visitech_LRS10_Device,
)
from .backend import (
    set_fn,
    Color,
    Polychannel,
    PolychannelShape,
    BezierCurveShape,
)
from .router import Router
