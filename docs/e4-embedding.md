# Embedding Devices
Prev: [Extra 3: Stitching Devices](e3-stitching.md)

Embedding lets you place a **complete device** (its own labels, shapes, and layers) **inside another device**. This is useful for printing a high‑resolution section inside a larger low‑resolution device.

Key ideas:

- Embedded devices are sliced separately, then injected into the parent device’s print layers.
- Offsets are computed **relative to the parent device’s center**.
- Z translations are preserved (child layers are shifted up/down in microns).
- Embedded devices can be emitted at **different resolutions** than the parent.
- By default, subcomponents **subtract their bounding box** from the parent (often desirable, but not always when embedding).

---

## Step 1 — Build a parent device

Create a normal device with labels and a bulk shape.

```python
from pymfcad import Device, Cube, Color

parent = Device(
	name="Parent",
	position=(0, 0, 0),
	layers=200,
	layer_size=0.015,
	px_count=(2560, 1600),
	px_size=0.0152,
)

parent.add_label("bulk", Color.from_name("gray", 127))
parent.add_label("void", Color.from_name("aqua", 127))

parent.add_bulk("bulk", Cube(parent._size, center=False), label="bulk")
```

---

## Step 2 — Build an embedded device

The embedded device can use a **different pixel size or layer size**. Its position is relative to the parent.

```python
from pymfcad import Device, Cube

child = Device(
	name="Inset",
	position=(0, 0, 0),  # parent pixels/layers
	layers=120,
	layer_size=0.0015,          # finer Z resolution
	px_count=(1920, 1080),
	px_size=0.00075,            # finer XY resolution
)

child.add_label("bulk", Color.from_name("gray", 127))
child.add_label("void", Color.from_name("aqua", 127))

child.add_bulk("bulk", Cube(child._size, center=False), label="bulk")
child.add_void(
	"channel",
	Cube((600, 40, 20)).translate((100, 280, 20)),
	label="void",
)
```

---

## Step 3 — Add the embedded device

```python
parent.add_subcomponent("inset", child.translate((100,100,100)))
```

You can also choose to **disable bounding‑box subtraction** for embedded devices (see below). 

When slicing:

- The child’s **center** is aligned relative to the parent’s **center**.
- Any child translation (x/y/z) compounds through the hierarchy.
- Z offsets are applied in microns to the child’s layers.

---

## Slicing

- When slicing embedded devices, make sure:

1) Your printer has each light engine properly defined
2) The light engine's names match the expected names for the printer (i.e. visitech, wintech)
3) Your printer definition has the xy_stage_available parameter set properly.
4) Your device sizes match the resolutions of the defined light engines.

---

## Bounding‑box subtraction (important)

By default, `add_subcomponent()` subtracts the **subcomponent’s bounding box** from the parent’s shapes. This is often critical for normal subcomponents (prevents double‑solid regions), but it can be **wrong for embedded devices** in two common cases:

1) **Overlap margins** — you may want a few pixels of overlap between the low‑res parent and the high‑res inset to ensure a strong connection.
2) **Inset smaller than the light engine** — if the high‑res device doesn’t fill the light engine’s full resolution, the automatic subtraction can create **unexposed gaps around the embedded device**.

In these cases, disable the default subtraction and define a **custom subtraction void** in the parent so you control exactly what gets removed:

```python
parent.add_subcomponent(
	"inset",
	child.translate((100, 100, 100)),
	subtract_bounding_box=False,
)

# Example: carve a custom void with overlap margin
overlap = 20  # pixels to keep overlapping between parent and child
void_size = (child._size[0] - 2 * overlap, child._size[1] - 2 * overlap, child._size[2])
void_pos = (child._position[0] + overlap, child._position[1] + overlap, child._position[2])
parent.add_void(
	"inset_clearance",
	Cube(void_size, center=False).translate(void_pos),
	label="void",
)
```

Guidelines:

- **Keep subtraction on** if the embedded device should carve out a full cavity the same size as the child.
- **Turn it off + add a custom void** if you need overlap margins or the child doesn’t span the full light engine.
- If results look hollowed unexpectedly or you see gaps around the inset, this is the first thing to check.

---

## Notes and limitations

- **Top‑level translation** only applies to image offsets if the printer has an **XY stage**.
- Embedded devices can be nested multiple levels deep; offsets are compounded through the hierarchy.
- If the embedded device has different resolution, it will be emitted at its **native resolution** with its own image offsets.

---

## Troubleshooting

- **Child Z not shifting** → make sure the child has a non‑zero Z position and non‑zero `layer_size`.
- **Offsets not applied** → check if the top‑level device has a translation and the printer lacks XY stage support.

---

Next: [Extra 5: Advanced TPMS Structures](e5-tpms_grids.md)

