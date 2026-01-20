# Embedding Devices
Prev: [Extra 3: Stitching Devices](e3-stitching.md)

Embedding lets you place a **complete device** (its own labels, shapes, and layers) **inside another device**. This is useful for printing a high‑resolution section inside a larger low‑resolution device.

Key ideas:

- Embedded devices are sliced separately, then injected into the parent device’s print layers.
- Offsets are computed **relative to the parent device’s center**.
- Z translations are preserved (child layers are shifted up/down in microns).

---

## Step 1 — Build a parent device

Create a normal device with labels and a bulk shape.

```python
from openmfd import Device, Cube, Color

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
from openmfd import Device, Cube

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

When slicing:

- The child’s **center** is aligned relative to the parent’s **center**.
- Any child translation (x/y/z) compounds through the hierarchy.
- Z offsets are applied in microns to the child’s layers.

---

## Notes and limitations

- **Top‑level translation** only applies to image offsets if the printer has an **XY stage**.
- Embedded devices can be nested multiple levels deep; offsets are compounded through the hierarchy.
- If the embedded device has different resolution, it will be emitted at its **native resolution** with its own image offsets.

---

## Troubleshooting

- **Child Z not shifting** → make sure the child has a non‑zero Z position and non‑zero `layer_size`.
- **Child XY misaligned** → verify the child is positioned relative to the parent and the parent is centered at the origin.
- **Offsets not applied** → check if the top‑level device has a translation and the printer lacks XY stage support.

---

Next: [Extra 5: Advanced TPMS Structures](e5-tpms_grids.md)

