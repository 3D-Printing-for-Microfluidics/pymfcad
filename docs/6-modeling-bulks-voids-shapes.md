# Modeling — Bulks, Voids, and Shapes

Prev: [Part 5: Modeling Introduction](5-modeling-introduction.md)

This step starts the **Modeling** section. Thoughout the **Modeling** section you will build a device in small, readable chunks. In this step you learn about **basic shapes** as well as how **bulks** and **voids** work together.

The basic example is a **cube void inside a cube bulk**. Then we expand into a **shape gallery** that shows every supported shape type side‑by‑side.

With both of these examples, the intent is for you to preview them yourself, and try changing some of the shapes and variables to see what happens. If you change the shape, there might be a different set of parameters to use when you declare it. Try using the **"Shapes (geometry)"** section of the **Cheat Sheet**.

The values to control shape sizes and operations (like translations) are set explicitly in each shape/operation. Later, we will learn how to use variables to simplify and standardize this process.

---

## Cube in a Cube

```python
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
```

---

## Shape gallery (side‑by‑side)

```python
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
imported = ImportModel("[YOUR FILE PATH HERE]")

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
```

![Shape gallery](resources/5-2.png)

---

![Device preview](resources/5-3.png)

---

## Notes

- **Bulks** are positive material. **Voids** are subtracted from bulks.
- `TPMS` and `ImportModel` can be heavier; try smaller sizes first.

---

## Next

Next: [Part 7: Modeling Microfluidics](7-modeling-microfluidics.md)