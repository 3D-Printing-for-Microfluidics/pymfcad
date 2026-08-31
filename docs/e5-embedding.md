# Embedding Devices
Prev: [Extra 4: Stitching Devices](e4-stitching.md)

Embedding is when you **nest components of different pixel sizes** inside each other. This is useful for printing a high‑resolution section inside a larger low‑resolution device.

By default, embedding just works — add a different-resolution component as a subcomponent and it will be sliced at its native resolution and positioned correctly. **Workspaces** provide advanced control over subcomponent light engine positioning via `adjust_subcomponent_light_engine_position()`.

Key ideas:

- Embedded components are sliced separately at their native resolution, then injected into the parent's print layers.
- Offsets are computed **relative to the parent component's center**.
- Z translations are preserved (child layers are shifted up/down in microns).
- Embedded components can have **different pixel sizes and layer sizes** than the parent.
- By default, subcomponents **subtract their bounding box** from the parent (prevents double‑solid regions).

---

## Basic embedding (without workspaces)

Embedding works automatically when you add a subcomponent with a different pixel size. Here's a practical example:

```python
from pymfcad import Component, Cube, Color, ExposureSettings

# Outer component (lower resolution, larger pixel size)
outer = Component(
	size=(2560, 1600, 120),
	layer_size=0.015,
	px_size=0.0152,
)

outer.add_default_exposure_settings(ExposureSettings(wavelength=405))
outer.add_label("bulk", Color.from_name("gray", 127))
outer.add_label("void", Color.from_name("aqua", 127))

outer_bulk = Cube(outer._size, center=False).translate(outer._position)
outer.add_bulk("outer_bulk", outer_bulk, label="bulk")

# Inner component (higher resolution, smaller pixel size)
inner = Component(
	size=(1920, 1080, 160),
	layer_size=0.0015,
	px_size=0.00075,
)

inner.add_default_exposure_settings(ExposureSettings(wavelength=365))
inner.add_label("bulk", Color.from_name("black", 127))
inner.add_label("void", Color.from_name("aqua", 127))

inner_bulk = Cube(inner._size, center=False).translate(inner._position)
inner.add_bulk("inner_bulk", inner_bulk, label="bulk")

# Add a void in the inner component
channel = Cube((inner._size[0], 40, 10)).translate((0, 100, 20))
inner.add_void("channel", channel, label="void")

# Embed the inner component into the outer component
# The inner component will be centered within the outer component's physical space
translation_x = (outer._size[0] * outer._px_size - inner._size[0] * inner._px_size) / 2
translation_y = (outer._size[1] * outer._px_size - inner._size[1] * inner._px_size) / 2
inner_translated = inner.translate(
	(translation_x / outer._px_size, translation_y / outer._px_size, 0)
)
outer.add_subcomponent("inner", inner_translated)

# Now slice normally
from pymfcad import PrintFileGenerator
from pymfcad.printer_library import MR1v1
from pymfcad.resin_library import NPS

print_file_gen = PrintFileGenerator(
	filename="embedded_device_demo",
	author="Test User",
	purpose="Test Design",
	description="A component with an embedded high-resolution section",
	component=outer,
	printer=MR1v1,
	resin=NPS,
	minimize_file=True,
	zip_output=False,
)

print_file_gen.run(overwrite=True, save_temp_files=False)
```

That's it! The outer component handles slicing at its resolution, and the inner component is automatically sliced at its finer resolution. Their geometries are merged correctly in the output.

---

## Advanced embedding (with workspaces)

For **fine-grained control** over which part of the light engine is used for a subcomponent, use **workspaces** with the `adjust_subcomponent_light_engine_position()` method.

This advanced approach is useful when you want to **use a different region of the projected light engine** for your subcomponent. The physical component position on the build platform stays exactly the same, but both the light engine position and the projected image are adjusted together, allowing you to choose a different part of the light engine field while maintaining physical consistency.

### Workspace embedding with light engine adjustment

```python
from pymfcad import Workspace, PrintFileGenerator
from pymfcad.printer_library import MR1v1
from pymfcad.resin_library import NPS

# Create workspaces and add the component
workspaces = [
	Workspace(
		printer=MR1v1,
		pixel_size=0.0152,  # Match outer component pixel size
		exposure_abs_pos_um=(0, 0),  # Build platform position
		light_engine_stitching=(1, 1),  # Single exposure (no stitching)
	)
]

# Add the component to the workspace
workspaces[0].add_component("OuterDevice", outer, centered=True)

# Adjust the inner component's light engine position
# (physical position stays the same, but LE position is nudged)
workspaces[0].adjust_subcomponent_light_engine_position("OuterDevice.inner", (50, 25))

# Slice with workspaces
print_file_gen = PrintFileGenerator(
	filename="embedded_device_demo",
	author="Test User",
	purpose="Test Design",
	description="Embedded component with LE position adjustment",
	workspaces=workspaces,
	printer=MR1v1,
	resin=NPS,
	minimize_file=True,
	zip_output=False,
)

print_file_gen.run(overwrite=True, save_temp_files=False)
```

The `adjust_subcomponent_light_engine_position()` call adjusts both the light engine position and the projected image offsets by the specified amount (in um). This shift is applied symmetrically — the LE position and image offsets move together — so the physical geometry on the build platform remains exactly the same. You're effectively choosing a different region of the light engine to use, while keeping the final printed result consistent.

---

## Bounding‑box subtraction (important)

By default, `add_subcomponent()` subtracts the **subcomponent's bounding box** from the parent's shapes. This is often critical for normal subcomponents (prevents double‑solid regions), but it can be **wrong for embedded components** in two common cases:

1) **Overlap margins** — you may want a few pixels of overlap between the low‑res parent and the high‑res inset to ensure a strong connection.

2) **Inset smaller than the light engine** — if the high‑res component doesn't fill the light engine's full resolution, the automatic subtraction can create **unexposed gaps around the embedded component**.

In these cases, disable the default subtraction and define a **custom subtraction void** in the parent so you control exactly what gets removed:

```python
outer.add_subcomponent(
	"inner",
	inner_translated,
	subtract_bounding_box=False,
)

# Example: carve a custom void with overlap margin
overlap = 20  # pixels to keep overlapping between parent and child
void_size = (inner._size[0] - 2 * overlap, inner._size[1] - 2 * overlap, inner._size[2])
void_pos = (inner._position[0] + overlap, inner._position[1] + overlap, inner._position[2])
outer.add_void(
	"inset_clearance",
	Cube(void_size, center=False).translate(void_pos),
	label="void",
)
```

Guidelines:

- **Keep subtraction on** if the embedded component should carve out a full cavity the same size as the child.
- **Turn it off + add a custom void** if you need overlap margins or the child doesn't span the full light engine.
- If results look hollowed unexpectedly or you see gaps around the inset, this is the first thing to check.

---

## Notes and limitations

- **Component positioning** works automatically through `add_subcomponent()` and center alignment.
- Embedded components can be nested multiple levels deep; offsets are compounded through the hierarchy.
- If the embedded component has different resolution, it will be emitted at its **native resolution** with its own image offsets.

---

## Troubleshooting

- **Component not appearing** → verify that the component was properly added as a subcomponent and that the physical positioning is correct.
- **Geometry looks misaligned** → check your translation calculations and verify the physical size/position of both components.
- **Quality issues** → use workspaces with `adjust_subcomponent_light_engine_position()` to fine-tune alignment if needed.

---

Next: [Extra 6: TPMS Grids](e6-tpms_grids.md)
