# Regional Settings

Prev: [Part 13: Slicing Settings](13-slicing-settings.md)

Regional settings let you override print behavior **inside specific 3D regions**. This is how you tune exposure or motion only where it matters—membranes, valve seats, channel roofs, or sensitive areas.

We’ll start with a 20 px valve **without** any regional settings, then add four region types:

- **Membrane** — on the membrane layer
- **Exposure** — higher exposure block between two fluidic channels below the fluidic chamber
- **Position** — reduced acceleration and speed above the membrane
- **Secondary** — reduced edge exposure around a vertical channel

---

## Step 1 — Base 20 px valve (no regional settings)

Start with the valve geometry and ports, but no regional settings.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -0 +1 @@
+import inspect
+from pymfcad import Component, Port, Color, Cylinder, Cube
+
+
+class Valve20px(Component):
+    def __init__(self, quiet: bool = False):
+        frame = inspect.currentframe()
+        args, _, _, values = inspect.getargvalues(frame)
+        self.init_args = [values[arg] for arg in args if arg != "self"]
+        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
+
+        super().__init__(
+            size=(36, 36, 24),
+            position=(0, 0, 0),
+            px_size=0.0076,
+            layer_size=0.01,
+            quiet=quiet,
+        )
+
+        self.add_label("device", Color.from_name("cyan", 255))
+        self.add_label("pneumatic", Color.from_name("red", 255))
+        self.add_label("fluidic", Color.from_name("blue", 255))
+        self.add_label("membrane", Color.from_name("green", 255))
+
+        self.add_bulk("BulkShape", Cube((36, 36, 24), center=False), label="device")
+
+        self.add_void(
+            "FluidicChamber",
+            Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 4)),
+            label="fluidic",
+        )
+        self.add_void(
+            "FluidicInput",
+            Cube((6, 6, 4), center=False).translate((15, 15, 0)),
+            label="fluidic",
+        )
+        self.add_void(
+            "FluidicOutput",
+            Cube((8, 10, 6), center=False).translate((14, 26, 0)),
+            label="fluidic",
+        )
+
+        pneumatics = Cylinder(height=11, radius=10, center_z=False).translate((18, 18, 7))
+        pneumatics += Cube((8, 10, 6), center=False).translate((14, 0, 12))
+        pneumatics += Cube((8, 10, 6), center=False).translate((14, 26, 12))
+        self.add_void("PneumaticShapes", pneumatics, label="pneumatic")
+
+        self.add_port(
+            "F_IN",
+            Port(Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.SurfaceNormal.NEG_Z),
+        )
+        self.add_port(
+            "F_OUT",
+            Port(Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.SurfaceNormal.POS_Y),
+        )
+        self.add_port(
+            "P_IN",
+            Port(Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
+        )
+        self.add_port(
+            "P_OUT",
+            Port(Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.SurfaceNormal.POS_Y),
+        )
    </script>
</div>

---

## Step 2 — Membrane region (on the membrane layer)

Membranes are thin layers that need special handling. Use `MembraneSettings` over the membrane layer to adjust exposure, apply defocus, and enable special techniques like `Print on Film`. It can also auto‑detect membranes within the region by finding areas thinner than `max_membrane_thickness_um` that are sandwiched between non‑exposed zones. If you already know the membrane area, set `scan_for_membrane=False` to use the region shape directly instead of scanning for membranes within that shape. Note: this also covers corner cases like print‑on‑film membranes with exposed pixels directly beneath them (for example, valves with 0‑layer‑thickness fluidic regions).

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import inspect
 from pymfcad import Component, Port, Color, Cylinder, Cube
+from pymfcad import MembraneSettings
 
 
 class Valve20px(Component):
     def __init__(self, quiet: bool = False):
         frame = inspect.currentframe()
         args, _, _, values = inspect.getargvalues(frame)
         self.init_args = [values[arg] for arg in args if arg != "self"]
         self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
 
         super().__init__(
             size=(36, 36, 24),
             position=(0, 0, 0),
             px_size=0.0076,
             layer_size=0.01,
             quiet=quiet,
         )
 
         self.add_label("device", Color.from_name("cyan", 255))
         self.add_label("pneumatic", Color.from_name("red", 255))
         self.add_label("fluidic", Color.from_name("blue", 255))
         self.add_label("membrane", Color.from_name("green", 255))
+        self.add_label("region_membrane", Color.from_name("violet", 127))
 
         self.add_bulk("BulkShape", Cube((36, 36, 24), center=False), label="device")
 
         self.add_void(
             "FluidicChamber",
             Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 4)),
             label="fluidic",
         )
         self.add_void(
             "FluidicInput",
             Cube((6, 6, 4), center=False).translate((15, 15, 0)),
             label="fluidic",
         )
         self.add_void(
             "FluidicOutput",
             Cube((8, 10, 6), center=False).translate((14, 26, 0)),
             label="fluidic",
         )
 
         pneumatics = Cylinder(height=11, radius=10, center_z=False).translate((18, 18, 7))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 0, 12))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 26, 12))
         self.add_void("PneumaticShapes", pneumatics, label="pneumatic")
 
         self.add_port(
             "F_IN",
             Port(Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.SurfaceNormal.NEG_Z),
         )
         self.add_port(
             "F_OUT",
             Port(Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )
         self.add_port(
             "P_IN",
             Port(Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
         )
         self.add_port(
             "P_OUT",
             Port(Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )

+        membrane_region = Cylinder(height=1, radius=10, center_z=False).translate((18, 18, 6))
+        self.add_regional_settings(
+            name="membrane_layer",
+            shape=membrane_region,
+            settings=MembraneSettings(
+                max_membrane_thickness_um=20,
+                bulk_exposure_multiplier=0.5,
+                defocus_um=50,
+                dilation_px=2,
+            ),
+            label="region_membrane",
+        )
    </script>
</div>

**What it does:** Forces membrane‑specific exposure on the membrane layer so it stays flexible and prints cleanly.

---

## Step 3 — Exposure region (between fluidic channels)

`ExposureSettings` lets you adjust exposure in a specific region. Here we boost exposure in a block between the two fluidic channels under the chamber to strengthen the thin wall that can be under‑cured or damaged under pressure.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import inspect
 from pymfcad import Component, Port, Color, Cylinder, Cube
-from pymfcad import MembraneSettings
+from pymfcad import MembraneSettings, ExposureSettings
 
 
 class Valve20px(Component):
     def __init__(self, quiet: bool = False):
         frame = inspect.currentframe()
         args, _, _, values = inspect.getargvalues(frame)
         self.init_args = [values[arg] for arg in args if arg != "self"]
         self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
 
         super().__init__(
             size=(36, 36, 24),
             position=(0, 0, 0),
             px_size=0.0076,
             layer_size=0.01,
             quiet=quiet,
         )
 
         self.add_label("device", Color.from_name("cyan", 255))
         self.add_label("pneumatic", Color.from_name("red", 255))
         self.add_label("fluidic", Color.from_name("blue", 255))
         self.add_label("membrane", Color.from_name("green", 255))
         self.add_label("region_membrane", Color.from_name("violet", 127))
+        self.add_label("region_exposure", Color.from_name("gold", 127))
 
         self.add_bulk("BulkShape", Cube((36, 36, 24), center=False), label="device")
 
         self.add_void(
             "FluidicChamber",
             Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 4)),
             label="fluidic",
         )
         self.add_void(
             "FluidicInput",
             Cube((6, 6, 4), center=False).translate((15, 15, 0)),
             label="fluidic",
         )
         self.add_void(
             "FluidicOutput",
             Cube((8, 10, 6), center=False).translate((14, 26, 0)),
             label="fluidic",
         )
 
         pneumatics = Cylinder(height=11, radius=10, center_z=False).translate((18, 18, 7))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 0, 12))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 26, 12))
         self.add_void("PneumaticShapes", pneumatics, label="pneumatic")
 
         self.add_port(
             "F_IN",
             Port(Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.SurfaceNormal.NEG_Z),
         )
         self.add_port(
             "F_OUT",
             Port(Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )
         self.add_port(
             "P_IN",
             Port(Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
         )
         self.add_port(
             "P_OUT",
             Port(Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )

         membrane_region = Cylinder(height=1, radius=10, center_z=False).translate((18, 18, 6))
         self.add_regional_settings(
             name="membrane_layer",
             shape=membrane_region,
             settings=MembraneSettings(
                 max_membrane_thickness_um=20,
                 bulk_exposure_multiplier=0.5,
                 defocus_um=50,
                 dilation_px=2,
                 scan_for_membrane=False,
             ),
             label="region_membrane",
         )

+        exposure_block = Cube((8, 4, 4), center=False).translate((14, 22, 0))
+        self.add_regional_settings(
+            name="fluidic_block",
+            shape=exposure_block,
+            settings=ExposureSettings(bulk_exposure_multiplier=2.0),
+            label="region_exposure",
+        )
    </script>
</div>

**What it does:** Locally increases exposure to strengthen the thin wall below the chamber.

---

## Step 4 — Position region (slower above membrane)

`PositionSettings` lets you adjust motion behavior in a specific region. Here we slow movement and reduce acceleration above the membrane to lower peel forces and reduce pressure spikes. If a path exists through the membrane to the outside of the device, overly aggressive motion can force resin through and burst the membrane.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import inspect
 from pymfcad import Component, Port, Color, Cylinder, Cube
-from pymfcad import MembraneSettings, ExposureSettings
+from pymfcad import MembraneSettings, ExposureSettings, PositionSettings
 
 
 class Valve20px(Component):
     def __init__(self, quiet: bool = False):
         frame = inspect.currentframe()
         args, _, _, values = inspect.getargvalues(frame)
         self.init_args = [values[arg] for arg in args if arg != "self"]
         self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
 
         super().__init__(
             size=(36, 36, 24),
             position=(0, 0, 0),
             px_size=0.0076,
             layer_size=0.01,
             quiet=quiet,
         )
 
         self.add_label("device", Color.from_name("cyan", 255))
         self.add_label("pneumatic", Color.from_name("red", 255))
         self.add_label("fluidic", Color.from_name("blue", 255))
         self.add_label("membrane", Color.from_name("green", 255))
         self.add_label("region_membrane", Color.from_name("violet", 127))
         self.add_label("region_exposure", Color.from_name("gold", 127))
+        self.add_label("region_position", Color.from_name("magenta", 127))
 
         self.add_bulk("BulkShape", Cube((36, 36, 24), center=False), label="device")
 
         self.add_void(
             "FluidicChamber",
             Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 4)),
             label="fluidic",
         )
         self.add_void(
             "FluidicInput",
             Cube((6, 6, 4), center=False).translate((15, 15, 0)),
             label="fluidic",
         )
         self.add_void(
             "FluidicOutput",
             Cube((8, 10, 6), center=False).translate((14, 26, 0)),
             label="fluidic",
         )
 
         pneumatics = Cylinder(height=11, radius=10, center_z=False).translate((18, 18, 7))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 0, 12))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 26, 12))
         self.add_void("PneumaticShapes", pneumatics, label="pneumatic")
 
         self.add_port(
             "F_IN",
             Port(Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.SurfaceNormal.NEG_Z),
         )
         self.add_port(
             "F_OUT",
             Port(Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )
         self.add_port(
             "P_IN",
             Port(Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
         )
         self.add_port(
             "P_OUT",
             Port(Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )

         membrane_region = Cylinder(height=1, radius=10, center_z=False).translate((18, 18, 6))
         self.add_regional_settings(
             name="membrane_layer",
             shape=membrane_region,
             settings=MembraneSettings(
                 max_membrane_thickness_um=20,
                 bulk_exposure_multiplier=0.5,
                 defocus_um=50,
                 dilation_px=2,
             ),
             label="region_membrane",
         )

         exposure_block = Cube((8, 4, 4), center=False).translate((14, 22, 0))
         self.add_regional_settings(
             name="fluidic_block",
             shape=exposure_block,
             settings=ExposureSettings(bulk_exposure_multiplier=2.0),
             label="region_exposure",
         )

+        position_region = Cylinder(height=12, radius=12, center_z=False).translate((18, 18, 7))
+        self.add_regional_settings(
+            name="slow_above_membrane",
+            shape=position_region,
+            settings=PositionSettings(
+                up_speed=10.0,
+                down_speed=10.0,
+                up_acceleration=20.0,
+                down_acceleration=20.0,
+            ),
+            label="region_position",
+        )
    </script>
</div>


**What it does:** Slows movement where the membrane is most fragile.

---

## Step 5 — Secondary dose region (reduced edge exposure)

Secondary dosing can be used to tune edge or roof exposure around features. Here, we **reduce** edge exposure around a vertical channel.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import inspect
 from pymfcad import Component, Port, Color, Cylinder, Cube
-from pymfcad import MembraneSettings, ExposureSettings, PositionSettings
+from pymfcad import MembraneSettings, ExposureSettings, PositionSettings, SecondaryDoseSettings
 
 
 class Valve20px(Component):
     def __init__(self, quiet: bool = False):
         frame = inspect.currentframe()
         args, _, _, values = inspect.getargvalues(frame)
         self.init_args = [values[arg] for arg in args if arg != "self"]
         self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
 
         super().__init__(
             size=(36, 36, 24),
             position=(0, 0, 0),
             px_size=0.0076,
             layer_size=0.01,
             quiet=quiet,
         )
 
         self.add_label("device", Color.from_name("cyan", 255))
         self.add_label("pneumatic", Color.from_name("red", 255))
         self.add_label("fluidic", Color.from_name("blue", 255))
         self.add_label("membrane", Color.from_name("green", 255))
         self.add_label("region_membrane", Color.from_name("violet", 127))
         self.add_label("region_exposure", Color.from_name("gold", 127))
         self.add_label("region_position", Color.from_name("magenta", 127))
+        self.add_label("region_secondary", Color.from_name("cyan", 127))
 
         self.add_bulk("BulkShape", Cube((36, 36, 24), center=False), label="device")
 
         self.add_void(
             "FluidicChamber",
             Cylinder(height=2, radius=10, center_z=False).translate((18, 18, 4)),
             label="fluidic",
         )
         self.add_void(
             "FluidicInput",
             Cube((6, 6, 4), center=False).translate((15, 15, 0)),
             label="fluidic",
         )
         self.add_void(
             "FluidicOutput",
             Cube((8, 10, 6), center=False).translate((14, 26, 0)),
             label="fluidic",
         )
 
         pneumatics = Cylinder(height=11, radius=10, center_z=False).translate((18, 18, 7))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 0, 12))
         pneumatics += Cube((8, 10, 6), center=False).translate((14, 26, 12))
         self.add_void("PneumaticShapes", pneumatics, label="pneumatic")
 
         self.add_port(
             "F_IN",
             Port(Port.PortType.IN, (15, 15, 0), (6, 6, 4), Port.SurfaceNormal.NEG_Z),
         )
         self.add_port(
             "F_OUT",
             Port(Port.PortType.OUT, (14, 36, 0), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )
         self.add_port(
             "P_IN",
             Port(Port.PortType.INOUT, (14, 0, 12), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
         )
         self.add_port(
             "P_OUT",
             Port(Port.PortType.INOUT, (14, 36, 12), (8, 8, 6), Port.SurfaceNormal.POS_Y),
         )

         membrane_region = Cylinder(height=1, radius=10, center_z=False).translate((18, 18, 6))
         self.add_regional_settings(
             name="membrane_layer",
             shape=membrane_region,
             settings=MembraneSettings(
                 max_membrane_thickness_um=20,
                 bulk_exposure_multiplier=0.5,
                 defocus_um=50,
                 dilation_px=2,
             ),
             label="region_membrane",
         )

         exposure_block = Cube((8, 4, 4), center=False).translate((14, 22, 0))
         self.add_regional_settings(
             name="fluidic_block",
             shape=exposure_block,
             settings=ExposureSettings(bulk_exposure_multiplier=2.0),
             label="region_exposure",
         )

         position_region = Cylinder(height=12, radius=12, center_z=False).translate((18, 18, 7))
         self.add_regional_settings(
             name="slow_above_membrane",
             shape=position_region,
             settings=PositionSettings(
                 up_speed=10.0,
                 down_speed=10.0,
                 up_acceleration=20.0,
                 down_acceleration=20.0,
             ),
             label="region_position",
         )

+        secondary_region = Cube((6, 6, 8), center=False).translate((15, 15, 0))
+        self.add_regional_settings(
+            name="vertical_channel_edges",
+            shape=secondary_region,
+            settings=SecondaryDoseSettings(
+                edge_bulk_exposure_multiplier=0.6,
+                edge_erosion_px=1,
+                edge_dilation_px=0,
+            ),
+            label="region_secondary",
+        )
    </script>
</div>

**What it does:** Reduces edge over‑cure around a vertical channel to keep features crisp.

---

## Tips

- Add regional settings **after voids** and **before bulk** so the regions align with the final geometry.
- Use distinct labels to visualize regions in the viewer.
- Regional settings override defaults only inside their shapes.

---

## Next

Next: [Part 15: Slicing Process](15-slicing-process.md)
