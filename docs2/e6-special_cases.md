# Special Printing Techniques
Prev: [Extra 5: Advanced TPMS Structures](e5-tpms_grids.md)

This extra explains **special techniques** that modify printing behavior. Each technique attaches to a specific settings object.

---

## Print‑level techniques (Settings)

Use these at the **job level** by passing them to `Settings(..., special_print_techniques=[...])`.

### Print under vacuum

```python
from openmfd import Settings, PrintUnderVacuum

vacuum = PrintUnderVacuum(
	enabled=True,
	target_vacuum_level_torr=10.0,
	vacuum_wait_time=30.0,
)

settings = Settings(
	printer=printer,
	resin=resin,
	default_position_settings=PositionSettings(),
	default_exposure_settings=ExposureSettings(),
	special_print_techniques=[vacuum],
)
```

This adds a **Print under vacuum** block to the JSON print settings.

**What it does:** Pulls a vacuum in the print chamber and runs the print under vacuum.

---

## Layer‑level techniques (PositionSettings)

These modify **motion per layer** and are attached to `PositionSettings`.

### Squeeze out resin

**What it does:** Drives the build platform to a target force beyond the programmed layer thickness. This helps resolve layer thickness issues, especially in **large print areas** and **very small layer thicknesses** (sub 5 um) or with **viscous resins**.

```python
from openmfd import PositionSettings, SqueezeOutResin

pos = PositionSettings(
	distance_up=1.0,
	final_wait=0.0,
	special_layer_techniques=[
		SqueezeOutResin(enabled=True, count=2, squeeze_force=5.0, squeeze_time=200.0)
	],
)
```

---

## Image‑level techniques (ExposureSettings)

These modify **exposure behavior** per layer and are attached to `ExposureSettings`.

### Zero‑micron layers

Repeats an exposure in a subsequent layer with a 0 um Z move between layers. This helps flush out partially polymerized material.

```python
from openmfd import ExposureSettings, ZeroMicronLayer

exp = ExposureSettings(
	exposure_time=250,
	special_image_techniques=[ZeroMicronLayer(enabled=True, count=2)],
)
```

### Print on film

Raises the build platform and exposes on film (not connected to bulk material/build platform). This allows flushing partially polymerized material beyond the layer in Z and enables very small Z voids or layers that are not attached to each other.

```python
from openmfd import ExposureSettings, PrintOnFilm

exp = ExposureSettings(
	exposure_time=250,
	special_image_techniques=[PrintOnFilm(enabled=True, distance_up_mm=0.3)],
)
```

---

## Notes

- Techniques are **optional** and can be mixed.
- If a technique is disabled (`enabled=False`), it’s preserved but ignored.
- These settings are serialized into the JSON print file under **Special print techniques** or **Special layer techniques**.
