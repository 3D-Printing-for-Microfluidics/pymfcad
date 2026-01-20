# Creating Your First Slicable Device
Prev: [Part 8: Designing Custom Subcomponents](8-making_subcomponent.md)

In this step, you will create a **device** (not just a component), attach slicing settings, and prepare it for the slicer. By the end, you will have a device that is ready to slice and export in Part 10.

## Why this step matters

OpenMFD distinguishes between **components** (reusable building blocks) and **devices** (printable assemblies tied to a specific printer/light engine). Slicing requires device-level information such as pixel size, pixel count, layer height, and exposure settings. This step bridges design and fabrication.

## What you will build

You will:

1. Create a device sized for your printer.
2. Add labels and a minimal bulk/void pair.
3. Define slicer settings (printer, resin, default position/exposure).
4. Save settings to JSON and re-load them (optional, but recommended).
5. Preview the device to visually verify it before slicing.

If you already have a component from earlier steps, you can skip the geometry portion and focus on the **device + settings** sections.

---

## Step 1 — Create a device (printer-aware)

Devices encode the printer geometry (pixel count, pixel size, layer size). For a Visitech LRS10-based printer you can use the built-in device class:

```python
from openmfd import Visitech_LRS10_Device

device = Visitech_LRS10_Device(
	name="MyFirstDevice",
	position=(0, 0, 0),
	layers=200,          # total layer count
	layer_size=0.01,     # mm per layer
)
```

**Checkpoint:** You should now have a `device` object that represents your printable build volume.

---

## Step 2 — Add labels, voids, and bulk

Slicable devices still follow the **void-in-bulk** model. You need at least one bulk shape and one void shape to see meaningful output.

```python
from openmfd import Color, Cube

device.add_label("bulk", Color.from_name("gray", 127))
device.add_label("fluidic", Color.from_name("aqua", 127))

# A simple fluidic void (channel)
channel = Cube((50, 10, 6))
channel.translate((20, 45, 20))
device.add_void("main_channel", channel, label="fluidic")

# Bulk block (must be added last)
bulk_cube = Cube(device._size, center=False)
bulk_cube.translate(device._position)
device.add_bulk("bulk", bulk_cube, label="bulk")
```

**Checkpoint:** If you call `device.preview()`, you should see a single rectangular channel cut through a solid block.

---

## Step 3 — Define slicer settings

Settings define the printer, resin, and default exposure/position behavior. Start with a minimal, explicit configuration. You can store settings to JSON so they can be reused by different devices.

```python
from openmfd import (
	Settings,
	ResinType,
	Printer,
	LightEngine,
	PositionSettings,
	ExposureSettings,
)

settings = Settings(
	printer=Printer(
		name="HR3v3",
		light_engines=[
			LightEngine(px_size=0.0076, px_count=(2560, 1600), wavelengths=[365])
		],
	),
	resin=ResinType(),
	default_position_settings=PositionSettings(),
	default_exposure_settings=ExposureSettings(),
)

settings.save("settings.json")
settings = Settings.from_file("settings.json")
```

**Checkpoint:** You should now have a `settings.json` file in your working directory.

---

## Settings objects (what they are and when to change them)

Think of `Settings` as the **print recipe** for the entire device. It contains printer hardware details, resin chemistry metadata, and default motion/exposure values applied to every layer unless overridden later.

### `Settings`

Container that bundles everything needed by the slicer.

- **You set it once per print** (or per device family).
- It stores **printer**, **resin**, and **default layer behavior**.
- It can be saved/loaded from JSON for repeatability.

### `Printer`

Describes the hardware platform (name + available light engines).

- The slicer uses this to validate geometry and pick the right light engine.
- If your printer has multiple light engines, list them all here.
- It can be saved/loaded from JSON for repeatability.

### `LightEngine`

Describes the optics that define pixel resolution.

- `name` links the link engine to the actual printer. It must be the same as the light engine name in the printer hardware config.
- `px_size` and `px_count` set the **physical resolution**.
- `wavelengths` is used to match the resin exposure wavelength.
- If your device size doesn’t match your light engine resolution, slicing will fail.

### `ResinType`

Metadata used for **traceability** and consistent settings across experiments.

- Tracks monomers, absorbers, initiators, and additives as percentages.
- These values are saved into the settings JSON and exported with the print file.

### `PositionSettings`

Controls **motion behavior** between layers (lift, speeds, waits, squeeze).

- Think of this as the mechanical side of the print.
- Use defaults unless you have a known motion profile to apply.

### `ExposureSettings`

Controls **light exposure behavior** per layer (time, power, wavelength).

- This is where you tune curing behavior.
- Use defaults first; adjust only after test prints.

---

## Step 3b — Device-level defaults (global print behavior)

In addition to `Settings`, you can attach **device/component-level defaults** that the slicer will apply to every layer unless you later specify regional overrides (covered in Part 12).

```python
from openmfd import ExposureSettings, PositionSettings

# Apply defaults to the whole device
device.add_default_exposure_settings(
	ExposureSettings(exposure_time=300.0, power_setting=100)
)
device.add_default_position_settings(
	PositionSettings(distance_up=1.0, up_speed=25.0, down_speed=20.0)
)

# Optional: burn-in layers (longer exposures at the start)
device.set_burn_in_exposure([600.0, 600.0, 450.0])
```

**Checkpoint:** If you later inspect the slicer output, the first three layers should use the burn-in exposure values above.

---

## Step 4 — Preview your device before slicing

Always preview the device to confirm:

- The channel is inside the bulk
- Labels are correct
- Nothing is missing or inverted

```python
device.preview()
```

**Checkpoint:** In the visualizer, the **Device** view should show a solid block with the channel removed.

---

## What’s next

In Part 10, you will run the slicer using the device and settings you created here, and generate a print file you can inspect.

Next: [Part 10: Slicing Process](10-slicing.md)
