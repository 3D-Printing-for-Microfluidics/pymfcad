import pymfcad
# Import shapes
from pymfcad import (
    Cube,
    RoundedCube,
    Cylinder,
    Sphere,
    TextExtrusion,
    TPMS,
    ImportModel,
)

# Initialize our Device, the "canvas" we work within
gallery = pymfcad.Device(
    name="overlapping_shapes",
    position=[0,0,0],
    px_count=(1200,750),
    layers=300,
    px_size=0.01,
    layer_size=0.01,
)

# Create labels
gallery.add_label("red", pymfcad.Color.from_name("red9", 200))
gallery.add_label("orange", pymfcad.Color.from_name("orange4", 200))
gallery.add_label("dark_orange", pymfcad.Color.from_name("orange9", 200))
gallery.add_label("green", pymfcad.Color.from_name("green6", 200))
gallery.add_label("light_blue", pymfcad.Color.from_name("cyan5", 200))
gallery.add_label("blue", pymfcad.Color.from_name("blue7", 255))
gallery.add_label("purple", pymfcad.Color.from_name("violet4", 200))

# Make our shapes (notice the differences between each shape in its declaration)
cube = Cube(size=[300,300,300], center=False)
rounded = RoundedCube(size=[300,300,300], radius=[75,75,75], center=False)
cylinder = Cylinder(height=300, radius=150, center_xy=False, center_z=False)
sphere = Sphere(size=[300,300,300], center=False)
text = TextExtrusion(text="A", height=150, font="OpenSans-Medium", font_size=430)
tpms = TPMS(size=[100,100,100], cells=[3,3,3], func=pymfcad.TPMS.gyroid, fill=0.0, refinement=10)
imported = ImportModel("docs/code_samples/3DBenchy.stl")

# There are 4 main ways to transform shapes:
# translate((x,y,z))
# rotate((rx,ry,rz))
# resize((x,y,z))
# and mirror((x,y,z))

# Resize the imported model
imported.resize([300,160,250])

# Move our shapes
cube.translate([0,0,0])
rounded.translate([450,0,0])
cylinder.translate([0,450,0])
sphere.translate([450,450,0])
text.translate([900,0,0])
tpms.translate([900,450,0])
imported.translate([1500,150,0])

# Add our shapes
gallery.add_bulk("cube", cube, "red")
gallery.add_bulk("rounded", rounded, "dark_orange")
gallery.add_bulk("cylinder", cylinder, "orange")
gallery.add_bulk("sphere", sphere, "green")
gallery.add_bulk("text", text, "light_blue")
gallery.add_bulk("tpms", tpms, "purple")
gallery.add_bulk("benchy", imported, "blue")

# send to visualizer for preview
gallery.preview()