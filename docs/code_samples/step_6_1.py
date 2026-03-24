import pymfcad
# Import shapes
from pymfcad import (
    Cube,
    RoundedCube,
    Cylinder,
    Sphere,
)

# Initialize our Device, the "canvas" we work within
overlapping_shapes = pymfcad.Device(
    name="overlapping_shapes",
    position=[0,0,0],
    px_count=(300,300),
    layers=300,
    px_size=0.01,
    layer_size=0.01,
)

# Create labels
overlapping_shapes.add_label("bulk", pymfcad.Color.from_name("aqua", 127)) # try changing the color and alpha values!
overlapping_shapes.add_label("void", pymfcad.Color.from_rgba((0, 255, 0, 255)))

# Make our shapes
inner_shape = RoundedCube(size=[200,200,200], radius=[30,30,30])
outer_shape = Cube(size=[300,300,300]) # try changing the size!

# Move our inner shape
inner_shape.translate(translation=[50,50,50])

# Add shapes to the Device
overlapping_shapes.add_void("inner", inner_shape, "void") # Name of shape, the shape itself (variable name), and label
overlapping_shapes.add_bulk("outer", outer_shape, "bulk")

# Send to visualizer for preview
overlapping_shapes.preview()