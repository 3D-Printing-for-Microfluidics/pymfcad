# Slicing Process

Prev: [Part 14: Regional Settings](14-regional-settings.md)

This final step shows how to slice a complete device. Use the device from Part 11/13, **replace the valve with your updated valve**, and then generate the print bundle.

Before you start:

- Make sure your updated valve class from Part 14 is saved as my_valve20px.py.
- Confirm you can run the Part 11 device build without errors.

---

## Step 1 — Full device (Part 11) + your updated valve

Replace the `Valve20px` import below with your new valve class, then run the full device build. This is the same assembly as Part 11 with the updated valve:

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import pymfcad
 from pymfcad import Device, Router, Port, Color, Cube, PolychannelShape, BezierCurveShape
 from pymfcad.component_library import Pinhole
 
 # Replace this import with your updated valve
-from pymfcad import Valve20px
+from my_valve20px import Valve20px
 
 from y_junction_mixer import YJunctionMixer
 from serpentine_channel import SerpentineChannel
 
 # Make sure the files are named my_valve20px.py, y_junction_mixer.py, and serpentine_channel.py and are in the same folder as this script. If you saved them elsewhere, update the import paths accordingly.
 
 PX_SIZE = 0.0076
 LAYER_SIZE = 0.01
 
 DEVICE_X = 2560
 DEVICE_Y = 1600
 DEVICE_Z = 300
 
 device = Device(
     name="full_device",
     position=(0, 0, 0),
     layers=DEVICE_Z,
     layer_size=LAYER_SIZE,
     px_count=(DEVICE_X, DEVICE_Y),
     px_size=PX_SIZE,
 )
 
 device.add_label("bulk", Color.from_name("aqua", 127))
 device.add_label("fluidic", Color.from_name("blue", 255))
 device.add_label("pneumatic", Color.from_name("red", 255))
 device.add_label("membrane", Color.from_name("green", 255))
 
 device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")
 
 # Inlet pinholes
 inlet_a = Pinhole()
 inlet_a.translate((0, 500 - inlet_a._size[1] / 2, DEVICE_Z / 2 - inlet_a._size[2] / 2))
 
 inlet_b = Pinhole()
 inlet_b.translate((0, (DEVICE_Y - 500) - inlet_b._size[1] / 2, DEVICE_Z / 2 - inlet_b._size[2] / 2))
 
 # Pneumatic pinholes
 pneumatic_a = Pinhole().rotate(90)
 pneumatic_a.translate((400 + pneumatic_a._size[0] / 2, 0, DEVICE_Z / 2 - pneumatic_a._size[2] / 2))
 
 pneumatic_b = Pinhole().rotate(-90)
 pneumatic_b.translate((400 - pneumatic_b._size[0] / 2, DEVICE_Y, DEVICE_Z / 2 - pneumatic_a._size[2] / 2))
 
 # 20 px valves (use your updated valve class)
 valve_a = Valve20px().rotate(-90)
 valve_a.translate((500, 500 + valve_a._size[0] / 2, DEVICE_Z / 2 - valve_a._size[2] / 2))
 
 valve_b = Valve20px().rotate(-90)
 valve_b.translate((500, (DEVICE_Y - 500) + valve_b._size[0] / 2, DEVICE_Z / 2 - valve_b._size[2] / 2))
 
 # Mixer + serpentine + outlet pinhole
 mixer = YJunctionMixer().translate((DEVICE_X / 3, DEVICE_Y / 2, 150))
 serp = SerpentineChannel()
 serp.translate((DEVICE_X / 2, 800 - serp._size[1] / 2, 150 - serp._size[2] / 2))
 outlet = Pinhole().rotate(180)
 outlet.translate((DEVICE_X, DEVICE_Y / 2 + outlet._size[1] / 2, DEVICE_Z / 2 - outlet._size[2] / 2))
 
 device.add_subcomponent("inlet_a", inlet_a)
 device.add_subcomponent("inlet_b", inlet_b)
 device.add_subcomponent("pneu_a", pneumatic_a)
 device.add_subcomponent("pneu_b", pneumatic_b)
 device.add_subcomponent("valve_a", valve_a)
 device.add_subcomponent("valve_b", valve_b)
 device.add_subcomponent("mixer", mixer)
 device.add_subcomponent("serp", serp)
 device.add_subcomponent("outlet", outlet)
 
 # Relabel to device‑level categories
 
 device.relabel(
     {
         "bulk": "bulk",
         "device": "bulk",
         "fluidic": "fluidic",
         "pneumatic": "pneumatic",
         "membrane": "membrane",
         "mixer.void": "fluidic",
         "serp.void": "fluidic",
         "inlet_a.void": "fluidic",
         "inlet_b.void": "fluidic",
         "outlet.void": "fluidic",
         "pneu_a.void": "pneumatic",
         "pneu_b.void": "pneumatic",
     },
     recursive=True,
 )
 
 # Routing (same as Part 11)
 router = Router(device, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
 
 router.autoroute_channel(inlet_a.port, valve_a.F_IN, label="fluidic", direction_preference=("Z", "Y", "X"))
 router.autoroute_channel(inlet_b.port, valve_b.F_IN, label="fluidic", direction_preference=("Z", "Y", "X"))
 router.autoroute_channel(valve_a.F_OUT, mixer.inlet1, label="fluidic")
 router.autoroute_channel(valve_b.F_OUT, mixer.inlet2, label="fluidic")
 router.autoroute_channel(mixer.outlet, serp.inlet, label="fluidic")
 
 view_path = [
     PolychannelShape(shape_type="cube", position=(0, 0, 0), size=(8, 8, 6)),
     PolychannelShape(position=(0, -serp._size[1] / 2, 0), size=(8, 8, 6)),
     PolychannelShape(position=(0, 0, -serp._size[2] / 2), size=(8, 8, 6)),
     PolychannelShape(position=(50, 0, 0), size=(0, 8, 6)),
     PolychannelShape(position=(20, 0, 0), size=(0, 100, 6)),
     PolychannelShape(position=(100, 0, 0), size=(0, 100, 6)),
     PolychannelShape(position=(20, 0, 0), size=(0, 8, 6)),
 ]
 router.route_with_polychannel(serp.outlet, outlet.port, view_path, label="fluidic")
 
 # Pneumatic control lines (Part 11)
 diff_x = valve_a.P_IN._position[0] - pneumatic_a.port._position[0] - valve_a.P_IN._size[0] / 2 - pneumatic_a.port._size[0] / 2
 diff_y = valve_a.P_IN._position[1] - pneumatic_a.port._position[1] - valve_a.P_IN._size[1] / 2 + pneumatic_a.port._size[1] / 2
 diff_z = valve_a.P_IN._position[2] - pneumatic_a.port._position[2]
 router.route_with_polychannel(
     pneumatic_a.port,
     valve_a.P_IN,
     [
         BezierCurveShape(
             control_points=[(3 * diff_x, diff_y / 2, 0), (-3 * diff_x, diff_y / 2, 0)],
             bezier_segments=20,
             position=(diff_x, diff_y, diff_z),
             size=(8, 8, 6),
             shape_type="cube",
             rounded_cube_radius=(3, 3, 3),
         )
     ],
     label="pneumatic",
 )

 diff_x = valve_b.P_IN._position[0] - pneumatic_b.port._position[0] - valve_b.P_IN._size[0] / 2 - pneumatic_b.port._size[0] / 2
 diff_y = valve_b.P_IN._position[1] - pneumatic_b.port._position[1] + valve_b.P_IN._size[1] / 2 + pneumatic_b.port._size[1] / 2
 diff_z = valve_b.P_IN._position[2] - pneumatic_b.port._position[2]
 router.route_with_polychannel(
     pneumatic_b.port,
     valve_b.P_IN,
     [
         BezierCurveShape(
             control_points=[(3 * diff_x, diff_y / 2, 0), (-3 * diff_x, diff_y / 2, 0)],
             bezier_segments=20,
             position=(diff_x, diff_y, diff_z),
             size=(8, 8, 6),
             shape_type="cube",
             rounded_cube_radius=(3, 3, 3),
         )
     ],
     label="pneumatic",
 )
 
 # Stub unused ports
 
 device.add_port("ctrl_a_stub", Port(Port.PortType.INOUT, (800, 0, 200), (8, 8, 6), Port.SurfaceNormal.NEG_Y))
 device.add_port("ctrl_b_stub", Port(Port.PortType.INOUT, (800, DEVICE_Y, 200), (8, 8, 6), Port.SurfaceNormal.POS_Y))
 
 router.autoroute_channel(valve_a.P_OUT, device.ports["ctrl_a_stub"], label="pneumatic", direction_preference=("Z", "X", "Y"))
 router.autoroute_channel(valve_b.P_OUT, device.ports["ctrl_b_stub"], label="pneumatic", direction_preference=("Z", "X", "Y"))
 
 device.connect_port(device.ports["ctrl_a_stub"])
 device.connect_port(device.ports["ctrl_b_stub"])
 
 # Finalize geometry
 router.finalize_routes()
    </script>
</div>

---

## Step 2 — Attach settings (Part 13)

Here you create the slicer settings profile so slicing can validate hardware compatibility and compute exposure and motion metadata.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -164 +164 @@
 # Finalize geometry
 router.finalize_routes()
+
+from pymfcad import (
+    Settings,
+    ResinType,
+    Printer,
+    LightEngine,
+    PositionSettings,
+    ExposureSettings,
+)
+
+settings = Settings(
+    printer=Printer(
+        name="OS1",
+        light_engines=[
+            LightEngine(px_size=0.0076, px_count=(2560, 1600), wavelengths=[365])
+        ],
+    ),
+    resin=ResinType(bulk_exposure=300.0),
+    default_position_settings=PositionSettings(),
+    default_exposure_settings=ExposureSettings(),
+)
+
+# Optional device‑level defaults
+
+device.add_default_exposure_settings(
+    ExposureSettings(bulk_exposure_multiplier=1.0, power_setting=100)
+)
+
+device.add_default_position_settings(
+    PositionSettings(distance_up=1.0, up_speed=25.0, down_speed=20.0)
+)
+
+# Optional: burn‑in exposures for early layers (ms)
+device.set_burn_in_exposure([10000.0, 5000.0, 2500.0])
    </script>
</div>

---

## Step 3 — Slice the device

This final step actually slices the device! This converts the geometry and settings into a print bundle (JSON + slices) for the printer pipeline.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -198 +198 @@
 # Optional: burn‑in exposures for early layers (ms)
 device.set_burn_in_exposure([10000.0, 5000.0, 2500.0])
+
+from pymfcad import Slicer
+
+slicer = Slicer(
+    device=device,
+    settings=settings,
+    filename="full_device_print",
+    minimize_file=True,
+    zip_output=True,
+)
+
+device.preview() # optional
+slicer.make_print_file()
    </script>
</div>

**Checkpoint:** You should get a new output ZIP (or folder) containing the JSON print file and the slice images.

---

## Conclusion and next resources

You’ve now gone from a parametric microfluidic model to a printer‑ready slice bundle. From here, explore:

- Advanced guidance in the [Advanced Topics](e1-recoloring_components.md)
- Output format details in the [JSON Print File Reference](r4-json_print_file_reference.md)
- As well as other the [Resources](r1-cheatsheet.md)
- The [API Reference](api/core.md) for full class and method coverage

---
