# Slicing Settings

Prev: [Part 12: Slicing Introduction](12-slicing-introduction.md)

This step focuses on the **Settings** object and related defaults used by the slicer. You’ll define printer, resin, exposure, and motion behavior, then optionally attach device‑level defaults like burn‑in layers.

Goal: build a minimal, reusable settings profile that matches your printer.

---

## Why settings matter

PyMFCAD distinguishes between **components** (reusable building blocks) and **devices** (printer‑aware assemblies). Slicing uses the **device** geometry **and** the settings to validate printer compatibility and generate correct exposure/motion metadata.

---

## Printer‑specific device helpers

Printer‑aware device helpers are available, such as `Device.with_visitech_1x(...)`, that match a selection of light‑engine geometries (image size, pixel size). If your geometry does not exist, either create your own helper or use a generic `Device` with your pixel size and resolution.

---

## Step 1 — Define slicer settings

Settings describe the printer, resin, and default exposure/motion behavior. Start with an explicit, minimal configuration and save it to JSON for reuse.

In the code below, you are creating a settings profile that matches your printer’s pixel grid and resin exposure baseline.

You can export/import `Settings`, `ResinType`, and `Printer` objects to JSON using their `save()` and `from_file()` methods.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -0 +1 @@
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
+    resin=ResinType(
+        bulk_exposure=450.0,
+        monomer=[("PEG", 100)],
+        uv_absorbers=[("NPS", 2.0)],
+        initiators=[("IRG", 1.0)],
+    ),
+    default_position_settings=PositionSettings(),
+    default_exposure_settings=ExposureSettings(),
+)
+
+# Optionally save/import settings
+# settings.save("settings.json")
+# settings = Settings.from_file("settings.json")
    </script>
</div>

---

## Settings objects (what they are and when to change them)

Think of `Settings` as the **print recipe** for the entire device. It contains printer hardware details, resin metadata, and default motion/exposure values applied to every layer unless overridden later. In practice you only need a small set of profiles; most changes are resin‑specific. Device‑level defaults can override these values when needed.

### `Settings`

Container that bundles everything needed by the slicer.

- **Set once per print** (or per device family).
- Stores **printer**, **resin**, and **default layer behavior**.
- Can be saved/loaded from JSON for repeatability.

### `Printer`

Describes the hardware platform (name + available light engines).

- Describes the printer’s physical hardware capabilities.
- If your printer has multiple light engines, list them all here.
- Can be saved/loaded from JSON for repeatability.

### `LightEngine`

Describes the optics that define pixel resolution.

- `name` links the light engine to the hardware configuration.
- `px_size` and `px_count` set the **physical resolution**.
- `wavelengths` lists the available wavelengths in the projector.
- If device size doesn’t match the light engine resolution, slicing will fail.
- If exposure settings use an unlisted light engine or an unavailable wavelength, slicing will fail.

### `ResinType`

Metadata used for **traceability** and consistent settings across experiments.

- Tracks monomers, absorbers, initiators, and additives as percentages.
- `bulk_exposure` sets base exposure time (ms) for bulk polymerization.
- `exposure_offset` is an optional offset (ms) before polymerization begins.
- Values are saved into the settings JSON and exported with the print file.
- Any changes to exposure time are made in multiples of the exposure information contained in the Resin.

### `PositionSettings`

Controls **motion behavior** between layers (lift, speeds, waits, squeeze).

- Think of this as the mechanical side of the print.
- Use defaults unless you have a known motion profile to apply.

### `ExposureSettings`

Controls **light exposure behavior** per layer (multiplier, power, wavelength).

- Use defaults first; adjust only after test prints.
- Exposure time is computed as $(bulk\_exposure - exposure\_offset) * multiplier + exposure\_offset$.

---

## Step 2 — Device‑level defaults (optional)

You can also attach exposure/position defaults to a device or component. These override the base `Settings` values for that scope (device‑wide when set on the top‑level device, or local when set on a component). Custom components can use this to enforce specific settings on their own layers.

Use this when a specific device or component needs different motion or exposure than your global defaults.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -27 +27 @@
 # Optionally save/import settings
 # settings.save("settings.json")
 # settings = Settings.from_file("settings.json")
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
@@ -1 +1 @@
 from pymfcad import (
     Settings,
     ResinType,
     Printer,
     LightEngine,
     PositionSettings,
     ExposureSettings,
 )
 
 # Create settings object
 settings = Settings(
     printer=Printer(
         name="OS1",
         light_engines=[
             LightEngine(px_size=0.0076, px_count=(2560, 1600), wavelengths=[365])
         ],
     ),
     resin=ResinType(
         bulk_exposure=450.0,
         monomer=[("PEG", 100)],
         uv_absorbers=[("NPS", 2.0)],
         initiators=[("IRG", 1.0)],
     ),
     default_position_settings=PositionSettings(),
     default_exposure_settings=ExposureSettings(),
 )

 # Optionally save/import settings
 # settings.save("settings.json")
 # settings = Settings.from_file("settings.json")
 
 # Not strictly needed as these are already the defaults
 device.add_default_exposure_settings(
     ExposureSettings(bulk_exposure_multiplier=1.0, power_setting=100)
 )
 device.add_default_position_settings(
     PositionSettings(distance_up=1.0, up_speed=25.0, down_speed=20.0)
 )
 
 # Set device burn-in
 device.set_burn_in_exposure([10000.0, 5000.0, 2500.0])
    </script>
</div>

---

## Next

Next: [Part 14: Regional Settings](14-regional-settings.md)
