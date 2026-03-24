# Modeling — Bulks, Voids, and Shapes

Prev: [Part 5: Modeling Introduction](5-modeling-introduction.md)

This step starts the **Modeling** section. Thoughout the **Modeling** section you will build a device in small, readable chunks. In this step you learn about **basic shapes** as well as how **bulks** and **voids** work together.

The basic example is a **cube void inside a cube bulk**. Then we expand into a **shape gallery** that shows every supported shape type side‑by‑side.

With both of these examples, the intent is for you to preview them yourself, and try changing some of the shapes and variables to see what happens. If you change the shape, there might be a different set of parameters to use when you declare it. Try using the **"Shapes (geometry)"** section of the **Cheat Sheet**.

The values to control shape sizes and operations (like translations) are set explicitly in each shape/operation. Later, we will learn how to use variables to simplify and standardize this process.

---

## Cube in a Cube

In this example, we’ll build a cube bulk with a smaller rounded cube void inside it.

### Step 1 — Import PyMFCAD and the shapes you need

We import `pymfcad` plus the specific shapes we’ll use.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/overlapping_shapes.py b/overlapping_shapes.py
index 0000000..1111111 100644
--- a/overlapping_shapes.py
+++ b/overlapping_shapes.py
@@ -0 +1 @@
+import pymfcad
+# Import shapes
+from pymfcad import (
+    Cube,
+    RoundedCube,
+    Cylinder,
+    Sphere,
+)
    </script>
</div>

### Step 2 — Create a Device

The `Device` is the 3D canvas we build inside. The size is controlled by pixel counts (x/y), layer count (z), and physical resolution (pixel size and layer size).

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/overlapping_shapes.py b/overlapping_shapes.py
index 0000000..1111111 100644
--- a/overlapping_shapes.py
+++ b/overlapping_shapes.py
@@ -1 +1 @@
 import pymfcad
 # Import shapes
 from pymfcad import (
     Cube,
     RoundedCube,
     Cylinder,
     Sphere,
 )
+
+# Initialize our Device, the "canvas" we work within
+overlapping_shapes = pymfcad.Device(
+    name="overlapping_shapes",
+    position=[0,0,0],
+    px_count=(300,300),
+    layers=300,
+    px_size=0.01,
+    layer_size=0.01,
+)
    </script>
</div>

### Step 3 — Add labels

Labels are named color groups used for visualization and organization. We’ll use one label for the bulk and another for the void. See the [Named Color Lists](r2-color.md) for available color names.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/overlapping_shapes.py b/overlapping_shapes.py
index 0000000..1111111 100644
--- a/overlapping_shapes.py
+++ b/overlapping_shapes.py
@@ -11 +11 @@
 overlapping_shapes = pymfcad.Device(
     name="overlapping_shapes",
     position=[0,0,0],
     px_count=(300,300),
     layers=300,
     px_size=0.01,
     layer_size=0.01,
 )
+
+# Create labels
+overlapping_shapes.add_label("bulk", pymfcad.Color.from_name("aqua", 127)) # try changing the color and alpha values!
+overlapping_shapes.add_label("void", pymfcad.Color.from_rgba((0, 255, 0, 255)))
    </script>
</div>

### Step 4 — Create the shapes

We’ll make a smaller rounded cube for the void and a larger cube for the bulk.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/overlapping_shapes.py b/overlapping_shapes.py
index 0000000..1111111 100644
--- a/overlapping_shapes.py
+++ b/overlapping_shapes.py
@@ -20 +20 @@
 # Create labels
 overlapping_shapes.add_label("bulk", pymfcad.Color.from_name("aqua", 127)) # try changing the color and alpha values!
 overlapping_shapes.add_label("void", pymfcad.Color.from_rgba((0, 255, 0, 255)))
+
+# Make our shapes
+inner_shape = RoundedCube(size=[200,200,200], radius=[30,30,30])
+outer_shape = Cube(size=[300,300,300]) # try changing the size!
    </script>
</div>

### Step 5 — Move the inner shape

We translate the inner shape so it sits inside the outer cube (not centered at the origin).

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/overlapping_shapes.py b/overlapping_shapes.py
index 0000000..1111111 100644
--- a/overlapping_shapes.py
+++ b/overlapping_shapes.py
@@ -24 +24 @@
 # Make our shapes
 inner_shape = RoundedCube(size=[200,200,200], radius=[30,30,30])
 outer_shape = Cube(size=[300,300,300]) # try changing the size!
+
+# Move our inner shape
+inner_shape.translate(translation=[50,50,50])
    </script>
</div>

### Step 6 — Add the bulk and void

Bulks add material; voids remove material from bulks. The order doesn’t matter for previewing, but both must be added to the same device.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/overlapping_shapes.py b/overlapping_shapes.py
index 0000000..1111111 100644
--- a/overlapping_shapes.py
+++ b/overlapping_shapes.py
@@ -28 +28 @@
 # Move our inner shape
 inner_shape.translate(translation=[50,50,50])
+
+# Add shapes to the Device
+overlapping_shapes.add_void("inner", inner_shape, "void") # Name of shape, the shape itself (variable name), and label
+overlapping_shapes.add_bulk("outer", outer_shape, "bulk")
    </script>
</div>

### Step 7 — Preview the result

Send the device to the visualizer so you can inspect it.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/overlapping_shapes.py b/overlapping_shapes.py
index 0000000..1111111 100644
--- a/overlapping_shapes.py
+++ b/overlapping_shapes.py
@@ -31 +31 @@
 # Add shapes to the Device
 overlapping_shapes.add_void("inner", inner_shape, "void") # Name of shape, the shape itself (variable name), and label
 overlapping_shapes.add_bulk("outer", outer_shape, "bulk")
+
+# Send to visualizer for preview
+overlapping_shapes.preview()
    </script>
</div>

![Cube in cube](resources/6/6-1.png)

### Full cube-in-cube example

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -1 +1 @@
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
    </script>
</div>

---

## Shape gallery (side‑by‑side)

This example lays out multiple shapes in a grid so you can compare them side‑by‑side.

### Step 1 — Import PyMFCAD and the shapes you need

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -0 +1 @@
+import pymfcad
+# Import shapes
+from pymfcad import (
+    Cube,
+    RoundedCube,
+    Cylinder,
+    Sphere,
+    TextExtrusion,
+    TPMS,
+    ImportModel,
+)
    </script>
</div>

### Step 2 — Create a Device

We use a larger canvas so all shapes can fit in a grid.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -1 +1 @@
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
+
+# Initialize our Device, the "canvas" we work within
+gallery = pymfcad.Device(
+    name="overlapping_shapes",
+    position=[0,0,0],
+    px_count=(1200,750),
+    layers=300,
+    px_size=0.01,
+    layer_size=0.01,
+)
    </script>
</div>

### Step 3 — Add labels

Each label gets a different color so the shapes are easy to identify.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -14 +14 @@
 gallery = pymfcad.Device(
     name="overlapping_shapes",
     position=[0,0,0],
     px_count=(1200,750),
     layers=300,
     px_size=0.01,
     layer_size=0.01,
 )
+
+# Create labels
+gallery.add_label("red", pymfcad.Color.from_name("red9", 200))
+gallery.add_label("orange", pymfcad.Color.from_name("orange4", 200))
+gallery.add_label("dark_orange", pymfcad.Color.from_name("orange9", 200))
+gallery.add_label("green", pymfcad.Color.from_name("green6", 200))
+gallery.add_label("light_blue", pymfcad.Color.from_name("cyan5", 200))
+gallery.add_label("blue", pymfcad.Color.from_name("blue7", 255))
+gallery.add_label("purple", pymfcad.Color.from_name("violet4", 200))
    </script>
</div>

### Step 4 — Create shapes

Notice how each shape has different parameters. This is where you can experiment with size, radius, font, or TPMS settings. For this step, we use the 3DBenchy model as an example for ImportModel. You can download it [here](https://www.thingiverse.com/thing:763622/files). Look for 3DBenchy.stl

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -23 +23 @@
 # Create labels
 gallery.add_label("red", pymfcad.Color.from_name("red9", 200))
 gallery.add_label("orange", pymfcad.Color.from_name("orange4", 200))
 gallery.add_label("dark_orange", pymfcad.Color.from_name("orange9", 200))
 gallery.add_label("green", pymfcad.Color.from_name("green6", 200))
 gallery.add_label("light_blue", pymfcad.Color.from_name("cyan5", 200))
 gallery.add_label("blue", pymfcad.Color.from_name("blue7", 255))
 gallery.add_label("purple", pymfcad.Color.from_name("violet4", 200))
+
+# Make our shapes (notice the differences between each shape in its declaration)
+cube = Cube(size=[300,300,300], center=False)
+rounded = RoundedCube(size=[300,300,300], radius=[75,75,75], center=False)
+cylinder = Cylinder(height=300, radius=150, center_xy=False, center_z=False)
+sphere = Sphere(size=[300,300,300], center=False)
+text = TextExtrusion(text="A", height=150, font="OpenSans-Medium", font_size=430)
+tpms = TPMS(size=[100,100,100], cells=[3,3,3], func=pymfcad.TPMS.gyroid, fill=0.0, refinement=10)
+imported = ImportModel("[YOUR FILE PATH HERE]")
    </script>
</div>

### Step 5 — Resize the imported model

`ImportModel` usually needs to be resized to fit the canvas.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -32 +32 @@
 # Make our shapes (notice the differences between each shape in its declaration)
 cube = Cube(size=[300,300,300], center=False)
 rounded = RoundedCube(size=[300,300,300], radius=[75,75,75], center=False)
 cylinder = Cylinder(height=300, radius=150, center_xy=False, center_z=False)
 sphere = Sphere(size=[300,300,300], center=False)
 text = TextExtrusion(text="A", height=150, font="OpenSans-Medium", font_size=430)
 tpms = TPMS(size=[100,100,100], cells=[3,3,3], func=pymfcad.TPMS.gyroid, fill=0.0, refinement=10)
 imported = ImportModel("[YOUR FILE PATH HERE]")
+
+# There are 4 main ways to transform shapes:
+# translate((x,y,z))
+# rotate((rx,ry,rz))
+# resize((x,y,z))
+# and mirror((x,y,z))
+
+# Resize the imported model
+imported.resize([300,160,250])
    </script>
</div>

### Step 6 — Arrange the shapes in a grid

We translate each shape to a unique position so they don’t overlap.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -47 +47 @@
 # Resize the imported model
 imported.resize([300,160,250])
+
+# Move our shapes
+cube.translate([0,0,0])
+rounded.translate([450,0,0])
+cylinder.translate([0,450,0])
+sphere.translate([450,450,0])
+text.translate([900,0,0])
+tpms.translate([900,450,0])
+imported.translate([1500,150,0])
    </script>
</div>

### Step 7 — Add shapes to the device

Each shape is added as a bulk and assigned its color label.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -50 +50 @@
 # Move our shapes
 cube.translate([0,0,0])
 rounded.translate([450,0,0])
 cylinder.translate([0,450,0])
 sphere.translate([450,450,0])
 text.translate([900,0,0])
 tpms.translate([900,450,0])
 imported.translate([1500,150,0])
+
+# Add our shapes
+gallery.add_bulk("cube", cube, "red")
+gallery.add_bulk("rounded", rounded, "dark_orange")
+gallery.add_bulk("cylinder", cylinder, "orange")
+gallery.add_bulk("sphere", sphere, "green")
+gallery.add_bulk("text", text, "light_blue")
+gallery.add_bulk("tpms", tpms, "purple")
+gallery.add_bulk("benchy", imported, "blue")
    </script>
</div>

### Step 8 — Preview the gallery

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -59 +59 @@
 # Add our shapes
 gallery.add_bulk("cube", cube, "red")
 gallery.add_bulk("rounded", rounded, "dark_orange")
 gallery.add_bulk("cylinder", cylinder, "orange")
 gallery.add_bulk("sphere", sphere, "green")
 gallery.add_bulk("text", text, "light_blue")
 gallery.add_bulk("tpms", tpms, "purple")
 gallery.add_bulk("benchy", imported, "blue")
+
+# send to visualizer for preview
+gallery.preview()
    </script>
</div>

![Shape gallery](resources/6/6-2.png)

### Full shape gallery example

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/shape_gallery.py b/shape_gallery.py
index 0000000..1111111 100644
--- a/shape_gallery.py
+++ b/shape_gallery.py
@@ -1 +1 @@
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
    </script>
</div>

---

## Notes

- **Bulks** are positive material. **Voids** are subtracted from bulks.
- `TPMS` and `ImportModel` can be heavier; try smaller sizes first.

---

## Next

Next: [Part 7: Modeling Microfluidics](7-modeling-microfluidics.md)