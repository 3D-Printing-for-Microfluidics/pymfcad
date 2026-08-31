# Full Device Assembly

Prev: [Part 10: Using Components in a Device](10-using-components.md)

This final modeling step builds a **complete microfluidic device** and introduces advanced techniques:

- **Bezier curve routing**
- **Polychannel routing**
- **Stubbing** unused ports
- **Relabeling** subcomponent labels
- **Rendering** to a file

Device plan:

- Two **inlets** → **20 px valves** → **Y‑junction mixer**
- Mixer output → **serpentine** → **expanded viewing area** → **outlet pinhole**
- Each valve control line connects to a **pinhole** on one side and a **stubbed external port** on the other

---

## Step 1 — Component context + labels + bulk

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -0 +1 @@
+from pymfcad import (
+    BezierCurveShape,
+    Color,
+    Component,
+    Cube,
+    PolychannelShape,
+    Port,
+    Router,
+)
+from pymfcad.component_library import Pinhole, Valve20px
+
+from .serpentine_channel import SerpentineChannel
+from .y_junction_mixer import YJunctionMixer
+
+PX_SIZE = 0.0076
+LAYER_SIZE = 0.01
+
+DEVICE_X = 2560
+DEVICE_Y = 1600
+DEVICE_Z = 300
+
+device = Component(
+    size=[DEVICE_X, DEVICE_Y, DEVICE_Z],
+    layer_size=LAYER_SIZE,
+    px_size=PX_SIZE,
+)
+
+device.add_label("bulk", Color.from_name("aqua", 127))
+device.add_label("fluidic", Color.from_name("blue", 255))
+device.add_label("pneumatic", Color.from_name("red", 255))
+device.add_label("membrane", Color.from_name("green", 255))
+
+device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")
+
+device.preview()
    </script>
</div>

Preview the bulk block.


<img
    class="theme-aware-image"
    alt="Device bulk"
    src="resources/11/11-1_dark.png"
    data-light-src="resources/11/11-1_light.png"
    data-dark-src="resources/11/11-1_dark.png"
/>

---

## Step 2 — Add subcomponents

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -33 +33 @@
 device.add_bulk("bulk_shape", Cube(device._size, center=False), label="bulk")
+
+# Inlet pinholes
+inlet_a = Pinhole()
+inlet_a.translate((0, 500 - inlet_a._size[1] / 2, DEVICE_Z / 2 - inlet_a._size[2] / 2))
+inlet_b = Pinhole()
+inlet_b.translate(
+    (0, (DEVICE_Y - 500) - inlet_b._size[1] / 2, DEVICE_Z / 2 - inlet_b._size[2] / 2)
+)
+
+# Pneumatic pinholes
+pneumatic_a = Pinhole().rotate(90)
+pneumatic_a.translate(
+    (400 + pneumatic_a._size[0] / 2, 0, DEVICE_Z / 2 - pneumatic_a._size[2] / 2)
+)
+pneumatic_b = Pinhole().rotate(-90)
+pneumatic_b.translate(
+    (400 - pneumatic_b._size[0] / 2, DEVICE_Y, DEVICE_Z / 2 - pneumatic_a._size[2] / 2)
+)
+
+# 20 px valves
+valve_a = Valve20px().rotate(-90)
+valve_a.translate((500, 500 + valve_a._size[0] / 2, DEVICE_Z / 2 - valve_a._size[2] / 2))
+valve_b = Valve20px().rotate(-90)
+valve_b.translate(
+    (500, (DEVICE_Y - 500) + valve_b._size[0] / 2, DEVICE_Z / 2 - valve_b._size[2] / 2)
+)
+
+# Mixer + serpentine + outlet pinhole
+mixer = YJunctionMixer().translate((DEVICE_X / 3, DEVICE_Y / 2, 150))
+serp = SerpentineChannel()
+serp.translate((DEVICE_X / 2, 800 - serp._size[1] / 2, 150 - serp._size[2] / 2))
+outlet = Pinhole().rotate(180)
+outlet.translate(
+    (DEVICE_X, DEVICE_Y / 2 + outlet._size[1] / 2, DEVICE_Z / 2 - outlet._size[2] / 2)
+)
+
+device.add_subcomponent("inlet_a", inlet_a)
+device.add_subcomponent("inlet_b", inlet_b)
+device.add_subcomponent("pneu_a", pneumatic_a)
+device.add_subcomponent("pneu_b", pneumatic_b)
+device.add_subcomponent("valve_a", valve_a)
+device.add_subcomponent("valve_b", valve_b)
+device.add_subcomponent("mixer", mixer)
+device.add_subcomponent("serp", serp)
+device.add_subcomponent("outlet", outlet)
 
 device.preview()
    </script>
</div>

Preview the device at this stage.

<img
    class="theme-aware-image"
    alt="Subcomponent placement"
    src="resources/11/11-2_dark.png"
    data-light-src="resources/11/11-2_light.png"
    data-dark-src="resources/11/11-2_dark.png"
/>

---

## Step 3 — Relabel subcomponents

Subcomponents bring their own labels (and colors). If you leave them as‑is, you’ll end up with many label names like `valve_a.pneumatic` or `mixer.void`. Use `relabel()` to **merge and normalize** those labels into a small, consistent component‑level set (e.g., `fluidic`, `pneumatic`, `membrane`, `bulk`).

This keeps the visualizer clean and makes downstream settings (like slicer regions) much easier to manage.

For more information see [Extra 1: Customizing Subcomponent Labels and Colors](e1-recoloring_components.md)

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -70 +70 @@
 device.add_subcomponent("inlet_a", inlet_a)
 device.add_subcomponent("inlet_b", inlet_b)
 device.add_subcomponent("pneu_a", pneumatic_a)
 device.add_subcomponent("pneu_b", pneumatic_b)
 device.add_subcomponent("valve_a", valve_a)
 device.add_subcomponent("valve_b", valve_b)
 device.add_subcomponent("mixer", mixer)
 device.add_subcomponent("serp", serp)
 device.add_subcomponent("outlet", outlet)
+
+device.relabel(
+    {
+        "bulk": "bulk",
+        "device": "bulk",
+        "fluidic": "fluidic",
+        "pneumatic": "pneumatic",
+        "membrane": "membrane",
+        "mixer.void": "fluidic",
+        "serp.void": "fluidic",
+        "inlet_a.void": "fluidic",
+        "inlet_b.void": "fluidic",
+        "outlet.void": "fluidic",
+        "pneu_a.void": "pneumatic",
+        "pneu_b.void": "pneumatic",
+    },
+    recursive=True,
+)
 
 device.preview()
    </script>
</div>

Preview again to confirm labels after relabeling.

### Before

<img
    class="theme-aware-image"
    alt="Device labels before relabeling"
    src="resources/11/11-3_dark.png"
    data-light-src="resources/11/11-3_light.png"
    data-dark-src="resources/11/11-3_dark.png"
/>

### After

<img
    class="theme-aware-image"
    alt="Device labels after relabeling"
    src="resources/11/11-4_dark.png"
    data-light-src="resources/11/11-4_light.png"
    data-dark-src="resources/11/11-4_dark.png"
/>

---

## Step 4 — Route fluidics (autoroute)

`route_with_polychannel()` is just like regular polychannel construction, **but the router automatically inserts the start and end port cross‑sections** for you. You only need to describe the shapes in between. It can be used when more advanced routing with multiple cross-sectional shapes/sizes are needed.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -80 +80 @@
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
+
+router = Router(device, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
+
+# Inlets → valves → mixer
+router.autoroute_channel(
+    inlet_a.port, valve_a.F_IN, label="fluidic", direction_preference=("Z", "Y", "X")
+)
+router.autoroute_channel(
+    inlet_b.port, valve_b.F_IN, label="fluidic", direction_preference=("Z", "Y", "X")
+)
+router.autoroute_channel(valve_a.F_OUT, mixer.inlet1, label="fluidic")
+router.autoroute_channel(valve_b.F_OUT, mixer.inlet2, label="fluidic")
+
+# Mixer → serpentine
+router.autoroute_channel(mixer.outlet, serp.inlet, label="fluidic")
+
+router.finalize_routes()
 
 device.preview()
    </script>
</div>

Preview the device after autorouting.

<img
    class="theme-aware-image"
    alt="Device with autorouting"
    src="resources/11/11-5_dark.png"
    data-light-src="resources/11/11-5_light.png"
    data-dark-src="resources/11/11-5_dark.png"
/>

---

## Step 5 — Polychannel routing (expanded viewing area)

This step creates a wider viewing region after the serpentine using a polychannel.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -110 +110 @@
 # Mixer → serpentine
 router.autoroute_channel(mixer.outlet, serp.inlet, label="fluidic")
+
+# Serpentine → expanded viewing area → outlet (polychannel routing)
+view_path = [
+    PolychannelShape(shape_type="cube", position=(0, 0, 0), size=(8, 8, 6)),
+    PolychannelShape(position=(0, -serp._size[1] / 2, 0), size=(8, 8, 6)),
+    PolychannelShape(position=(0, 0, -serp._size[2] / 2), size=(8, 8, 6)),
+    PolychannelShape(position=(50, 0, 0), size=(0, 8, 6)),
+    PolychannelShape(position=(20, 0, 0), size=(0, 100, 6)),
+    PolychannelShape(position=(100, 0, 0), size=(0, 100, 6)),
+    PolychannelShape(position=(20, 0, 0), size=(0, 8, 6)),
+]
+router.route_with_polychannel(serp.outlet, outlet.port, view_path, label="fluidic")
 
 router.finalize_routes()
 
 device.preview()
    </script>
</div>

Preview the device after polychannel routing.

<img
    class="theme-aware-image"
    alt="Device with polychannel routing (closeup)"
    src="resources/11/11-6_dark.png"
    data-light-src="resources/11/11-6_light.png"
    data-dark-src="resources/11/11-6_dark.png"
/>

---

## Step 6 — Pneumatic control lines (Bezier routing)

While there’s no functional requirement to use Bezier curves here, we use them simply to **introduce the technique**. Bezier routing is helpful when you want smooth curves or graceful detours.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -123 +123 @@
 router.route_with_polychannel(serp.outlet, outlet.port, view_path, label="fluidic")
+
+diff_x = (
+    valve_a.P_IN._position[0]
+    - pneumatic_a.port._position[0]
+    - valve_a.P_IN._size[0] / 2
+    - pneumatic_a.port._size[0] / 2
+)
+diff_y = (
+    valve_a.P_IN._position[1]
+    - pneumatic_a.port._position[1]
+    - valve_a.P_IN._size[1] / 2
+    + pneumatic_a.port._size[1] / 2
+)
+diff_z = valve_a.P_IN._position[2] - pneumatic_a.port._position[2]
+router.route_with_polychannel(
+    pneumatic_a.port,
+    valve_a.P_IN,
+    [
+        BezierCurveShape(
+            control_points=[(3 * diff_x, diff_y / 2, 0), (-3 * diff_x, diff_y / 2, 0)],
+            bezier_segments=50,
+            position=(diff_x, diff_y, diff_z),
+            size=(8, 8, 6),
+            shape_type="cube",
+            rounded_cube_radius=(3, 3, 3),
+        )
+    ],
+    label="pneumatic",
+)
+
+diff_x = (
+    valve_b.P_IN._position[0]
+    - pneumatic_b.port._position[0]
+    - valve_b.P_IN._size[0] / 2
+    - pneumatic_b.port._size[0] / 2
+)
+diff_y = (
+    valve_b.P_IN._position[1]
+    - pneumatic_b.port._position[1]
+    + valve_b.P_IN._size[1] / 2
+    + pneumatic_b.port._size[1] / 2
+)
+diff_z = valve_b.P_IN._position[2] - pneumatic_b.port._position[2]
+router.route_with_polychannel(
+    pneumatic_b.port,
+    valve_b.P_IN,
+    [
+        BezierCurveShape(
+            control_points=[(3 * diff_x, diff_y / 2, 0), (-3 * diff_x, diff_y / 2, 0)],
+            bezier_segments=50,
+            position=(diff_x, diff_y, diff_z),
+            size=(8, 8, 6),
+            shape_type="cube",
+            rounded_cube_radius=(3, 3, 3),
+        )
+    ],
+    label="pneumatic",
+)
 
 router.finalize_routes()
 
 device.preview()
    </script>
</div>

Preview the device after Bezier routing.
<img
    class="theme-aware-image"
    alt="Device with bezier routing (closeup)"
    src="resources/11/11-7_dark.png"
    data-light-src="resources/11/11-7_light.png"
    data-dark-src="resources/11/11-7_dark.png"
/>

---

## Step 7 — Add external flushing ports (autoroute only)

First add the external ports and autoroute the connections

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -167 +167 @@
 router.route_with_polychannel(
     pneumatic_b.port,
     valve_b.P_IN,
     [
         BezierCurveShape(
             control_points=[(3 * diff_x, diff_y / 2, 0), (-3 * diff_x, diff_y / 2, 0)],
             bezier_segments=50,
             position=(diff_x, diff_y, diff_z),
             size=(8, 8, 6),
             shape_type="cube",
             rounded_cube_radius=(3, 3, 3),
         )
     ],
     label="pneumatic",
 )
+
+# External flushing ports
+device.add_port(
+    "ctrl_a_stub",
+    Port(Port.PortType.INOUT, (800, 0, 200), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
+)
+device.add_port(
+    "ctrl_b_stub",
+    Port(Port.PortType.INOUT, (800, DEVICE_Y, 200), (8, 8, 6), Port.SurfaceNormal.POS_Y),
+)
+
+router.autoroute_channel(
+    valve_a.P_OUT,
+    device.ports["ctrl_a_stub"],
+    label="pneumatic",
+    direction_preference=("Z", "X", "Y"),
+)
+router.autoroute_channel(
+    valve_b.P_OUT,
+    device.ports["ctrl_b_stub"],
+    label="pneumatic",
+    direction_preference=("Z", "X", "Y"),
+)
 
 router.finalize_routes()
 
 device.preview()
    </script>
</div>

Preview the device after adding the external ports.

<img
    class="theme-aware-image"
    alt="Device with routed external ports"
    src="resources/11/11-8_dark.png"
    data-light-src="resources/11/11-8_light.png"
    data-dark-src="resources/11/11-8_dark.png"
/>

---

## Step 8 — Stub unused ports

If a port exists but isn’t used in this build, or is only used internally like the flushing channes, **stub** them so they don’t appear as unconnected.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -193 +193 @@
 router.autoroute_channel(
     valve_a.P_OUT,
     device.ports["ctrl_a_stub"],
     label="pneumatic",
     direction_preference=("Z", "X", "Y"),
 )
 router.autoroute_channel(
     valve_b.P_OUT,
     device.ports["ctrl_b_stub"],
     label="pneumatic",
     direction_preference=("Z", "X", "Y"),
 )
 
 router.finalize_routes()
+
+# Mark them as connected so they don’t show as unconnected ports
+device.connect_port(device.ports["ctrl_a_stub"])
+device.connect_port(device.ports["ctrl_b_stub"])
 
 device.preview()
    </script>
</div>

Preview the device after stubbing.

<img
    class="theme-aware-image"
    alt="Device with routed external ports (stubbed)"
    src="resources/11/11-9_dark.png"
    data-light-src="resources/11/11-9_light.png"
    data-dark-src="resources/11/11-9_dark.png"
/>

---

## Step 9 — Render device

Rendering exports the device as a **portable 3D model file** so it can be used outside the pymfcad ecosystem. Any component can be rendered. The output is the final **bulk‑void** model, ready for other CAD tools and manufacturing pipelines. We support common formats like **.glb**, **.stl**, and **.3mf**, so your design works across most 3D workflows without relying on our custom printers. Advanced settings (which we will introduce shortly), will not be exported.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -208 +208 @@
 # Mark them as connected so they don’t show as unconnected ports
 device.connect_port(device.ports["ctrl_a_stub"])
 device.connect_port(device.ports["ctrl_b_stub"])
 
 device.preview()
+
+# Render to a file for sharing or slicing
+device.render("full_device.stl")
+device.render("full_device.glb")
+device.render("full_device.3mf")
    </script>
</div>

<img
    class="theme-aware-image"
    alt="Final Device"
    src="resources/11/11-10_dark.png"
    data-light-src="resources/11/11-10_light.png"
    data-dark-src="resources/11/11-10_dark.png"
/>

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
 from pymfcad import (
     BezierCurveShape,
     Color,
     Component,
     Cube,
     PolychannelShape,
     Port,
     Router,
 )
 from pymfcad.component_library import Pinhole, Valve20px
 
 from .serpentine_channel import SerpentineChannel
 from .y_junction_mixer import YJunctionMixer
 
 PX_SIZE = 0.0076
 LAYER_SIZE = 0.01
 
 DEVICE_X = 2560
 DEVICE_Y = 1600
 DEVICE_Z = 300
 
 device = Component(
     size=[DEVICE_X, DEVICE_Y, DEVICE_Z],
     layer_size=LAYER_SIZE,
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
 inlet_b.translate(
     (0, (DEVICE_Y - 500) - inlet_b._size[1] / 2, DEVICE_Z / 2 - inlet_b._size[2] / 2)
 )
 
 # Pneumatic pinholes
 pneumatic_a = Pinhole().rotate(90)
 pneumatic_a.translate(
     (400 + pneumatic_a._size[0] / 2, 0, DEVICE_Z / 2 - pneumatic_a._size[2] / 2)
 )
 pneumatic_b = Pinhole().rotate(-90)
 pneumatic_b.translate(
     (400 - pneumatic_b._size[0] / 2, DEVICE_Y, DEVICE_Z / 2 - pneumatic_a._size[2] / 2)
 )
 
 # 20 px valves
 valve_a = Valve20px().rotate(-90)
 valve_a.translate((500, 500 + valve_a._size[0] / 2, DEVICE_Z / 2 - valve_a._size[2] / 2))
 valve_b = Valve20px().rotate(-90)
 valve_b.translate(
     (500, (DEVICE_Y - 500) + valve_b._size[0] / 2, DEVICE_Z / 2 - valve_b._size[2] / 2)
 )
 
 # Mixer + serpentine + outlet pinhole
 mixer = YJunctionMixer().translate((DEVICE_X / 3, DEVICE_Y / 2, 150))
 serp = SerpentineChannel()
 serp.translate((DEVICE_X / 2, 800 - serp._size[1] / 2, 150 - serp._size[2] / 2))
 outlet = Pinhole().rotate(180)
 outlet.translate(
     (DEVICE_X, DEVICE_Y / 2 + outlet._size[1] / 2, DEVICE_Z / 2 - outlet._size[2] / 2)
 )
 
 device.add_subcomponent("inlet_a", inlet_a)
 device.add_subcomponent("inlet_b", inlet_b)
 device.add_subcomponent("pneu_a", pneumatic_a)
 device.add_subcomponent("pneu_b", pneumatic_b)
 device.add_subcomponent("valve_a", valve_a)
 device.add_subcomponent("valve_b", valve_b)
 device.add_subcomponent("mixer", mixer)
 device.add_subcomponent("serp", serp)
 device.add_subcomponent("outlet", outlet)
 
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
 
 router = Router(device, channel_size=(8, 8, 6), channel_margin=(8, 8, 6))
 
 # Inlets → valves → mixer
 router.autoroute_channel(
     inlet_a.port, valve_a.F_IN, label="fluidic", direction_preference=("Z", "Y", "X")
 )
 router.autoroute_channel(
     inlet_b.port, valve_b.F_IN, label="fluidic", direction_preference=("Z", "Y", "X")
 )
 router.autoroute_channel(valve_a.F_OUT, mixer.inlet1, label="fluidic")
 router.autoroute_channel(valve_b.F_OUT, mixer.inlet2, label="fluidic")
 
 # Mixer → serpentine
 router.autoroute_channel(mixer.outlet, serp.inlet, label="fluidic")
 
 # Serpentine → expanded viewing area → outlet (polychannel routing)
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
 
 diff_x = (
     valve_a.P_IN._position[0]
     - pneumatic_a.port._position[0]
     - valve_a.P_IN._size[0] / 2
     - pneumatic_a.port._size[0] / 2
 )
 diff_y = (
     valve_a.P_IN._position[1]
     - pneumatic_a.port._position[1]
     - valve_a.P_IN._size[1] / 2
     + pneumatic_a.port._size[1] / 2
 )
 diff_z = valve_a.P_IN._position[2] - pneumatic_a.port._position[2]
 router.route_with_polychannel(
     pneumatic_a.port,
     valve_a.P_IN,
     [
         BezierCurveShape(
             control_points=[(3 * diff_x, diff_y / 2, 0), (-3 * diff_x, diff_y / 2, 0)],
             bezier_segments=50,
             position=(diff_x, diff_y, diff_z),
             size=(8, 8, 6),
             shape_type="cube",
             rounded_cube_radius=(3, 3, 3),
         )
     ],
     label="pneumatic",
 )
 
 diff_x = (
     valve_b.P_IN._position[0]
     - pneumatic_b.port._position[0]
     - valve_b.P_IN._size[0] / 2
     - pneumatic_b.port._size[0] / 2
 )
 diff_y = (
     valve_b.P_IN._position[1]
     - pneumatic_b.port._position[1]
     + valve_b.P_IN._size[1] / 2
     + pneumatic_b.port._size[1] / 2
 )
 diff_z = valve_b.P_IN._position[2] - pneumatic_b.port._position[2]
 router.route_with_polychannel(
     pneumatic_b.port,
     valve_b.P_IN,
     [
         BezierCurveShape(
             control_points=[(3 * diff_x, diff_y / 2, 0), (-3 * diff_x, diff_y / 2, 0)],
             bezier_segments=50,
             position=(diff_x, diff_y, diff_z),
             size=(8, 8, 6),
             shape_type="cube",
             rounded_cube_radius=(3, 3, 3),
         )
     ],
     label="pneumatic",
 )
 
 # External flushing ports
 device.add_port(
     "ctrl_a_stub",
     Port(Port.PortType.INOUT, (800, 0, 200), (8, 8, 6), Port.SurfaceNormal.NEG_Y),
 )
 device.add_port(
     "ctrl_b_stub",
     Port(Port.PortType.INOUT, (800, DEVICE_Y, 200), (8, 8, 6), Port.SurfaceNormal.POS_Y),
 )
 
 router.autoroute_channel(
     valve_a.P_OUT,
     device.ports["ctrl_a_stub"],
     label="pneumatic",
     direction_preference=("Z", "X", "Y"),
 )
 router.autoroute_channel(
     valve_b.P_OUT,
     device.ports["ctrl_b_stub"],
     label="pneumatic",
     direction_preference=("Z", "X", "Y"),
 )
 
 router.finalize_routes()
 
 # Mark them as connected so they don’t show as unconnected ports
 device.connect_port(device.ports["ctrl_a_stub"])
 device.connect_port(device.ports["ctrl_b_stub"])
 
 device.preview()
 
 # Render to a file for sharing or slicing
 device.render("full_device.stl")
 device.render("full_device.glb")
 device.render("full_device.3mf")
    </script>
</div>

---

## Notes

- **Bezier routing** is great for pneumatic lines and smooth curves.
- **Polychannel routing** lets you expand or taper channels mid‑path.
- **Relabeling** keeps all geometry under a small, consistent set of labels.
- **Stubbing** hides unused ports without deleting them.

---

## Next

Next: [Part 12: Slicing Introduction](12-slicing-introduction.md)