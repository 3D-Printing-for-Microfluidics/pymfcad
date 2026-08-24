from pymfcad import (
    Color,
    Component,
    Cube,
    PrintFileGenerator,
)
from pymfcad.printer_library import OS1v0
from pymfcad.resin_library import NPS

# 2x2 stitched device (overall resolution = 5120 x 3200)
device = Component(
    size=(5116, 3196, 50),
    layer_size=0.01,
    px_size=0.0076,
)

# Labels
device.add_label("bulk", Color.from_name("gray", 127))
device.add_label("void", Color.from_name("aqua", 127))

# Simple void channel
width, height = device._size[0], device._size[1]
channel1 = Cube((width, 40, 10)).translate((0, 200, 20))
channel2 = Cube((width, 40, 10)).translate((0, height - 200, 20))
channel3 = Cube((40, height, 10)).translate((200, 0, 20))
channel4 = Cube((40, height, 10)).translate((width - 200, 0, 20))
device.add_void("channel1", channel1, label="void")
device.add_void("channel2", channel2, label="void")
device.add_void("channel3", channel3, label="void")
device.add_void("channel4", channel4, label="void")

# Bulk block (add last)
bulk = Cube(device._size, center=False)
bulk.translate(device._position)
device.add_bulk("bulk_shape", bulk, label="bulk")

device.preview()

# Printer with XY stage required for stitched devices

OS1v0.light_engines[0].stitched_px_overlap = (4, 4)  # set overlap for the light engine

# Slice
slicer = PrintFileGenerator(
    filename="stitched_demo",
    component=device,
    printer=OS1v0,
    resin=NPS,
    minimize_file=True,
    zip_output=False,
)

slicer.run(overwrite=True)
