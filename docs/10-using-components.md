# Using Components in a Device

Prev: [Part 9: Routing with Fractional Paths](9-routing-fractional.md)

This step shows how to assemble a full device from **subcomponents**, apply **component operations**, and use **autoroute** when you don’t need strict path control.

We’ll build a device with:

- Two **inlet pinholes** feeding a **Y‑junction**
- A **serpentine** between the Y‑junction and the outlet
- One **outlet pinhole**

---

## Component operations (quick recap)

Subcomponents are just components placed inside a larger device. You can transform them before adding them:

- `translate((x, y, z))` moves the component
- `rotate(x)` rotates it in degrees (multiples of 90)
- `mirror(mirror_x, mirror_y)` mirrors it across axes

These operations make it easy to reuse the same component in multiple orientations.

---

## Step 1 — Device context

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -0 +1 @@
+import pymfcad
+from pymfcad import Component, Router, Color, Cube
+from pymfcad.component_library import Pinhole
+
+# Import custom components from previous steps
+from y_junction_mixer import YJunctionMixer
+from serpentine_channel import SerpentineChannel
+
+# Make sure the files are named y_junction_mixer.py and serpentine_channel.py and are in the same folder as this script. If you saved them elsewhere, update the import path accordingly.
+
+PX_SIZE = 0.0076
+LAYER_SIZE = 0.01
+
+DEVICE_X = 2560
+DEVICE_Y = 1600
+DEVICE_Z = 300
+
+# Create a new device (final print = bulk minus voids)
+device = pymfcad.Device(
+    name="example_device",
+    position=(0, 0, 0),
+    layers=DEVICE_Z,
+    layer_size=LAYER_SIZE,
+    px_count=(DEVICE_X, DEVICE_Y),
+    px_size=PX_SIZE,
+)
+
+device.add_label("bulk", Color.from_name("aqua", 127))
+device.add_label("void", Color.from_name("red", 255))
+
+device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")
+
+device.preview()
    </script>
</div>

Preview the empty device canvas.


![Step 1 preview](resources/10/10-1.png)

---

## Step 2 — Add subcomponents (pinholes, Y‑junction, serpentine)

`Pinhole` is a **prebuilt** component from `pymfcad.component_library` that provides a standardized access port geometry. We’ll reuse it for the two inlets and one outlet.

At this stage you are only placing components in space; the channels that connect them will be routed in the next step.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -31 +31 @@
 device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")
+
+# Inlet pinholes (left side, pointing into the device)
+inlet_a = Pinhole()
+inlet_a.translate(
+    (0, 
+    500 - inlet_a._size[1]/2, 
+    DEVICE_Z/2 - inlet_a._size[2]/2
+    )
+)
+inlet_b = Pinhole()
+inlet_b.translate(
+    (0, 
+    (DEVICE_Y - 500) - inlet_b._size[1]/2, 
+    DEVICE_Z/2 - inlet_b._size[2]/2
+    )
+)
+# Y‑junction near the left side
+y = YJunctionMixer()
+y.translate((DEVICE_X/3, DEVICE_Y/2, DEVICE_Z/2 - y._size[2]/2))
+
+# Serpentine between Y‑junction and outlet
+serp = SerpentineChannel()
+serp.translate((DEVICE_X/2, 800 - serp._size[1]/2, DEVICE_Z/2 - serp._size[2]/2))
+
+# Outlet pinhole on the right side (flip to face inward)
+outlet = Pinhole().rotate(180)
+outlet.translate(
+    (DEVICE_X, 
+    DEVICE_Y/2 + outlet._size[1]/2, 
+    DEVICE_Z/2 - outlet._size[2]/2
+    )
+)
+
+device.add_subcomponent("inlet_a", inlet_a)
+device.add_subcomponent("inlet_b", inlet_b)
+device.add_subcomponent("y", y)
+device.add_subcomponent("serp", serp)
+device.add_subcomponent("outlet", outlet)
 
 device.preview()
    </script>
</div>

Preview component placement before routing.

![Step 2 preview](resources/10/10-2.png)

---

## Step 3 — Autoroute between ports

If you don’t need strict control of the path, **autoroute** is faster and cleaner. You can also set a **direction preference** to bias the search (for example, prefer X‑moves before Y‑moves).

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -69 +69 @@
 device.add_subcomponent("outlet", outlet)
+
+router = Router(device, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
+
+# Inlets into the Y‑junction
+router.autoroute_channel(
+    inlet_a.port,
+    y.inlet1,
+    label="void",
+    direction_preference=("X", "Y", "Z"),
+)
+router.autoroute_channel(
+    inlet_b.port,
+    y.inlet2,
+    label="void",
+    direction_preference=("X", "Y", "Z"),
+)
+
+# Y‑junction to serpentine
+router.autoroute_channel(
+    y.outlet,
+    serp.inlet,
+    label="void",
+    direction_preference=("X", "Y", "Z"),
+)
+
+# Serpentine to outlet pinhole
+router.autoroute_channel(
+    serp.outlet,
+    outlet.port,
+    label="void",
+    direction_preference=("Z", "Y", "X"),
+)
+
+router.finalize_routes()
 
 device.preview()
    </script>
</div>

Preview the routed device. 

![Step 3 preview](resources/10/10-3.png)

---

## Full example

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import pymfcad
 from pymfcad import Component, Router, Color, Cube
 from pymfcad.component_library import Pinhole
 
 # Import custom components from previous steps
 from y_junction_mixer import YJunctionMixer
 from serpentine_channel import SerpentineChannel
 
 # Make sure the files are named y_junction_mixer.py and serpentine_channel.py and are in the same folder as this script. If you saved them elsewhere, update the import path accordingly.
 
 PX_SIZE = 0.0076
 LAYER_SIZE = 0.01
 
 DEVICE_X = 2560
 DEVICE_Y = 1600
 DEVICE_Z = 300
 
 # Create a new device (final print = bulk minus voids)
 device = pymfcad.Device(
     name="example_device",
     position=(0, 0, 0),
     layers=DEVICE_Z,
     layer_size=LAYER_SIZE,
     px_count=(DEVICE_X, DEVICE_Y),
     px_size=PX_SIZE,
 )
 
 device.add_label("bulk", Color.from_name("aqua", 127))
 device.add_label("void", Color.from_name("red", 255))
 
 device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")
 
 # Inlet pinholes (left side, pointing into the device)
 inlet_a = Pinhole()
 inlet_a.translate(
     (0, 
     500 - inlet_a._size[1]/2, 
     DEVICE_Z/2 - inlet_a._size[2]/2
     )
 )
 inlet_b = Pinhole()
 inlet_b.translate(
     (0, 
     (DEVICE_Y - 500) - inlet_b._size[1]/2, 
    DEVICE_Z/2 - inlet_b._size[2]/2
    )
 )
 # Y‑junction near the left side
 y = YJunctionMixer()
 y.translate((DEVICE_X/3, DEVICE_Y/2, DEVICE_Z/2 - y._size[2]/2))
 
 # Serpentine between Y‑junction and outlet
 serp = SerpentineChannel()
 serp.translate((DEVICE_X/2, 800 - serp._size[1]/2, DEVICE_Z/2 - serp._size[2]/2))
 
 # Outlet pinhole on the right side (flip to face inward)
 outlet = Pinhole().rotate(180)
 outlet.translate(
     (DEVICE_X, 
     DEVICE_Y/2 + outlet._size[1]/2, 
     DEVICE_Z/2 - outlet._size[2]/2
     )
 )
 
 device.add_subcomponent("inlet_a", inlet_a)
 device.add_subcomponent("inlet_b", inlet_b)
 device.add_subcomponent("y", y)
 device.add_subcomponent("serp", serp)
 device.add_subcomponent("outlet", outlet)
 
 router = Router(device, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
 
 # Inlets into the Y‑junction
 router.autoroute_channel(
     inlet_a.port,
     y.inlet1,
     label="void",
     direction_preference=("X", "Y", "Z"),
 )
 router.autoroute_channel(
     inlet_b.port,
     y.inlet2,
     label="void",
     direction_preference=("X", "Y", "Z"),
 )
 
 # Y‑junction to serpentine
 router.autoroute_channel(
     y.outlet,
     serp.inlet,
     label="void",
     direction_preference=("X", "Y", "Z"),
 )
 
 # Serpentine to outlet pinhole
 router.autoroute_channel(
     serp.outlet,
     outlet.port,
     label="void",
     direction_preference=("Z", "Y", "X"),
 )
 
 device.preview()
    </script>
</div>

---

## Notes

- Use **subcomponents** to build devices from reusable building blocks.
- **Autoroute** is ideal when path shape is not critical.
- Use `direction_preference=("X", "Y", "Z")` to bias routing order.

---

## Next

Next: [Part 11: Full Device Assembly](11-full-device.md)