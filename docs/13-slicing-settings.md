# Slicing Settings

Prev: [Part 12: Slicing Introduction](12-slicing-introduction.md)

This step focuses on the printer, resin, exposure, and motion settings used by `PrintFileGenerator`. You’ll define a printer and resin profile, then optionally attach component-level defaults like burn-in layers.

Goal: build a minimal, reusable settings profile that matches your printer.

---

## Why settings matter

PyMFCAD components contain reusable geometry and can also represent complete assemblies. `PrintFileGenerator` uses the component geometry and settings together with the printer and resin profiles to validate component compatibility and generate exposure/motion metadata for a print file.

---

## Printer and light-engine matching

The printer provides one or more light engines that define the available pixel sizes and projection areas. Your printer must have a light engine matching the pixel size used by your component.

---

## Printer and resin libraries

PyMFCAD includes printer and resin libraries with predefined profiles for commonly used hardware and materials. Use a library profile when it matches your setup:

```python
from pymfcad.printer_library import OS1v0
from pymfcad.resin_library import NPS

printer = OS1v0
resin = NPS
```

The printer library includes `HR3v3`, `HR5`, `MR1v1`, and `OS1v0`. The resin library includes `NPS`, `AVO`, `AVO_TPO`, and formulations with 1% or 10% crosslinker. Library objects are regular `Printer` and `ResinType` objects, so they can be passed directly to `PrintFileGenerator` or saved and customized like manually created profiles. Define your own profiles when your printer or resin differs from the available library entries.

---

## Step 1 — Define printer and resin inputs

The printer and resin describe the hardware and material used for the print. Below are examples from the resin and printer library (OS1v0 printer and 2% NPS resin). Optionally, you can modify and save each profile to JSON files for reuse.



You can export/import `ResinType` and `Printer` objects to JSON using their `save()` and `from_file()` methods.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -0 +1 @@
+from pymfcad import (
+    ResinType,
+    Printer,
+    LightEngine,
+    PositionSettings,
+    ExposureSettings,
+)
+
+printer = Printer(
+    name="OS1v0",
+    light_engines=[
+        LightEngine(
+            name="visitech",
+            px_size=0.0076,
+            px_count=(2560, 1600),
+            wavelengths=[365],
+            default_exposure_settings=[
+                ExposureSettings(
+                    grayscale_correction=True,
+                    bulk_exposure_multiplier=1.0,
+                    power_setting=100,
+                    wavelength=365,
+                )
+            ],
+            grayscale_available=[True],
+            settle_time_ms=0.0,
+            stitched_px_overlap=(0, 0),
+            x_offset_limits=(-9728, 9728),
+            y_offset_limits=(-6080, 6080),
+        )
+    ],
+    xy_stage_available=True,
+    vacuum_available=False,
+    default_position_settings=PositionSettings(),
+)
+
+resin = ResinType(
+    bulk_exposure=450,
+    exposure_offset=0.0,
+    monomer=[("PEG", 100)],
+    uv_absorbers=[("NPS", 2.0)],
+    initiators=[("IRG", 1.0)],
+    additives=[],
+)
+
+# Optionally save/import settings
+# printer.save("OS1v0_printer.json")
+# printer = Printer.from_file("OS1v0_printer.json")
+# resin.save("NPS_resin.json")
+# resin = ResinType.from_file("NPS_resin.json")
    </script>
</div>

---

## Settings objects (what they are and when to change them)

The following objects divide the print recipe into hardware, material, exposure, and motion information. In practice you only need a small set of profiles; most changes are resin-specific. Component-level defaults can override the general values when needed.

### `Printer`

Describes the hardware platform.

- Describes the printer’s physical hardware capabilities.
- If your printer has multiple light engines, list them all here.
- Can be saved/loaded from JSON for repeatability.

### `LightEngine`

Describes the optics that define pixel resolution.

- `name` links the light engine to the hardware configuration.
- `px_size` and `px_count` set the **physical resolution**.
- `wavelengths` lists the available wavelengths in the projector.
- `default_exposure_settings` lists default settings for each light engine.
- `grayscale_available` lists the availability of grayscale for each light engine
- `settle_time_ms` adds an extra wait before the **first exposure** after switching to this light engine.
- `stitched_px_overlay` and the `offset_limits` configure stitching for each light engine.
- If the component size does not fit the selected light-engine projection area, slicing will use projection or stitching as appropriate.
- If exposure settings use an unlisted light engine or an unavailable wavelength, slicing will fail.

### `ResinType`

Metadata used for **traceability** and consistent settings across experiments.

- Tracks monomers, absorbers, initiators, and additives as percentages.
- `bulk_exposure` sets base exposure time (ms) for bulk polymerization.
- `exposure_offset` is an optional offset (ms) before polymerization begins.
- Values are saved into the resin JSON and exported with the print file.
- Any changes to exposure time are made in multiples of the exposure information contained in the Resin.

### `PositionSettings` (in printer definition)

Controls **motion behavior** between layers (lift, speeds, waits, squeeze).

- Think of this as the mechanical side of the print.
- Use defaults unless you have a known motion profile to apply.

### `ExposureSettings` (in light engine definition)

Controls **light exposure behavior** per layer (multiplier, power, wavelength).

- Use defaults first; adjust only after test prints.
- Exposure time is computed as $(bulk\_exposure - exposure\_offset) * multiplier + exposure\_offset$.

---

## Step 2 — Component‑level defaults (optional)

You can attach exposure/position defaults to any component. These override general values for that component (defaults inherited from parent components and printer definition) and can enforce specific settings on its own layers.

If you set `use_parent_settings=True` in the Component contructor, the component will inherits its setting directly from its parent. Components using this option cannot add their own settings. Use this option for purely geometric components such as pinholes and resevoirs.

Use this when a specific component or assembly needs different motion or exposure than your general defaults.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -27 +27 @@
 # Optionally save/import settings
 # printer.save("OS1v0_printer.json")
 # printer = Printer.from_file("OS1v0_printer.json")
 # resin.save("NPS_resin.json")
 # resin = ResinType.from_file("NPS_resin.json")
+
+# Not strictly needed as these are already the defaults
+device.add_default_exposure_settings(
+    ExposureSettings(bulk_exposure_multiplier=1.0, power_setting=100)
+)
+device.add_default_position_settings(
+    PositionSettings(distance_up=1.0, up_speed=25.0, down_speed=20.0)
+)
    </script>
</div>

## Step 3 — Burn‑in settings

Burn‑in layers are the first few layers of a print that use **longer exposures** to improve initial adhesion and stability. They can also help compensate for build‑platform leveling inconsistencies. Use burn‑in when you need stronger early layers (e.g., large flat bases or thin features that tend to detach). Burn‑in values are **absolute times in milliseconds**, not multipliers of the resin exposure.

The list below applies one exposure time per initial layer, in order.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -31 +31 @@
 # Not strictly needed as these are already the defaults
 device.add_default_exposure_settings(
     ExposureSettings(bulk_exposure_multiplier=1.0, power_setting=100)
 )
 device.add_default_position_settings(
     PositionSettings(distance_up=1.0, up_speed=25.0, down_speed=20.0)
 )
+
+# Optional: burn‑in exposures for early layers (ms)
+device.set_burn_in_exposure([10000.0, 5000.0, 2500.0])
    </script>
</div>

---

## Example — Prepare the Part 11 device

If you built the full device in Part 11, place the following **directly under that code** to attach settings, defaults, and burn‑in:

This example mirrors the minimal settings above, but adds resin metadata and explicit defaults so you can reuse the same settings file across prints.

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
 
 # Render to a file for sharing or slicing
-device.render("full_device.stl")
-device.render("full_device.glb")
-device.render("full_device.3mf")
+#device.render("full_device.stl")
+#device.render("full_device.glb")
+#device.render("full_device.3mf")
+
+from pymfcad import (
+    ExposureSettings
+    PositionSettings,
+)
+
+# Use predefined printer and resin (or use your own custom objects as shown above)
+from pymfcad.printer_library import OS1v0
+from pymfcad.resin_library import NPS
+printer = OS1v0
+resin = NPS
+
+# Not strictly needed as these are already the defaults
+device.add_default_exposure_settings(
+    ExposureSettings(bulk_exposure_multiplier=1.0, power_setting=100)
+)
+device.add_default_position_settings(
+    PositionSettings(distance_up=1.0, up_speed=25.0, down_speed=20.0)
+)
+
+# Set device burn-in
+device.set_burn_in_exposure([10000.0, 5000.0, 2500.0])
    </script>
</div>

---

## Next

Next: [Part 14: Regional Settings](14-regional-settings.md)
