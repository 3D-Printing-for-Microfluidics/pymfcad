from pymfcad import (
    Component,
    ExposureSettings,
    Color,
    Cube,
    PrintFileGenerator,
)

# Outer device (lower resolution, larger pixel size)
outer = Component(
    size=(2560, 1600, 120),
    layer_size=0.015,
    px_size=0.0152,
)

outer.add_default_exposure_settings(ExposureSettings(wavelength=405))

outer.add_label("bulk_outer", Color.from_name("gray", 127))
outer.add_label("void", Color.from_name("aqua", 127))

# Outer bulk
outer_bulk = Cube(outer._size, center=False).translate(outer._position)
outer.add_bulk("outer_bulk", outer_bulk, label="bulk_outer")

# Inner device (higher resolution, smaller pixel/layer size)
inner = Component(
    size=(1920, 1080, 160),
    layer_size=0.0015,
    px_size=0.00075,
)

inner.add_default_exposure_settings(ExposureSettings(wavelength=365))

inner.add_label("bulk_inner", Color.from_name("black", 127))
inner.add_label("void", Color.from_name("aqua", 127))

inner_bulk = Cube(inner._size, center=False).translate(inner._position)
inner.add_bulk("inner_bulk", inner_bulk, label="bulk_inner")

# A simple void in the inner device
channel = Cube((inner._size[0], 40, 10)).translate((0, 100, 20))
inner.add_void("channel", channel, label="void")

# Embed the inner device into the outer device
# calculate translation (center inner device within outer device)
translation_x = (outer._size[0]*outer._px_size - inner._size[0]*inner._px_size) / 2
translation_y = (outer._size[1]*outer._px_size - inner._size[1]*inner._px_size) / 2
inner.translate((translation_x / outer._px_size, translation_y / outer._px_size, 0))  # translation in outer device pixels/layers
outer.add_subcomponent("inner", inner)

outer.preview()


from pymfcad import Workspace
from pymfcad.printer_library import MR1v1
from pymfcad.resin_library import NPS

workspaces = [Workspace(MR1v1, outer._px_size, exposure_abs_pos_um=(0, 0), light_engine_stitching=(0,0))]
workspaces[0].add_component("OuterDevice", outer, centered=True)
workspaces[0].adjust_subcomponent_light_engine_position("OuterDevice.inner", (0,0))

print_file_gen = PrintFileGenerator(
    filename="embedded_device_demo",
    author="Test User",
    purpose="Test Design",
    description="This is a test design for the PyMFCAD library.",
    # component=outer,
    workspaces=workspaces,
    printer=MR1v1,
    resin=NPS,
    minimize_file=True,
    zip_output=False,
)

print_file_gen.run(overwrite=True, save_temp_files=False)
