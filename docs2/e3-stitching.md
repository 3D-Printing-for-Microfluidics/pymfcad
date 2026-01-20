# Stitching Devices
Prev: [Extra 2: Variable Layer Thickness Components](e2-variable_layer_thickness_components.md)

Stitching is used when a device is **larger than a single light engine field of view**. The idea is to print the device in an $n \times m$ grid of tiles, each with its own **X/Y image offset** in the JSON print file.

This workflow is advanced and currently requires defining a **custom device type** whose resolution is an integer multiple of the base light‑engine resolution.

---

## How stitching works (conceptual)

1. **Define a stitched device** whose pixel dimensions are $n \times m$ tiles of the base light engine.
2. **Slice each tile** with its own image offset.
3. **Write JSON settings** where each tile uses the same image stack but different `Image x offset (um)` and `Image y offset (um)`.

---

## Step 1 — Create a stitched device type

You need a device with pixel dimensions that are exact multiples of the light engine resolution:

$$
(W, H) = (n \cdot W_0,\; m \cdot H_0)
$$

Where $(W_0, H_0)$ is the base light engine resolution.

OpenMFD provides a `StitchedDevice` helper for this (optional `overlap_px` in pixels):

```python
from openmfd import StitchedDevice

device = StitchedDevice(
	name="StitchedChip",
	position=(0, 0, 0),
	layers=200,
	layer_size=0.01,
	tiles_x=2,
	tiles_y=2,
	base_px_count=(2560, 1600),
	overlap_px=4,
	px_size=0.0076,
)
```

**Checkpoint:** The stitched device width/height are 2×2 the base resolution.

**Requirement:** The printer must have an **X/Y stage** for stitched printing.

---

## Step 2 — Set per‑tile offsets

Each tile uses the same layers but different image offsets. If you add overlap, each tile steps by $(W_0-\text{overlap},\; H_0-\text{overlap})$ instead of $W_0,H_0$:

- `Image x offset (um)`
- `Image y offset (um)`

Offsets are computed from the tile index and the light engine pixel size. Each tile uses the same slice images, but with different offsets in the JSON output. The stitched device is **centered** in the print region by default.

**Tip:** Choose overlap in pixels, e.g. $\text{overlap\_px} = \lceil \text{overlap\_mm} / \text{px\_size} \rceil$.

---

## Practical limitations

- Slicing and output size scale with $n \times m$.
- Stitching requires careful alignment and calibration of the X/Y stage.
- Large devices may need custom post‑processing or printer‑side stitching logic.

---

## When to use stitching

- Devices larger than a single projector field
- Multi‑tile chips that cannot be shrunk or rotated to fit

---

Next: [Extra 4: Embedding Devices](e4-embedding.md)

