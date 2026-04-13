# Advanced TPMS Structures
Prev: [Extra 4: Embedding Devices](e4-embedding.md)

TPMS (Triply Periodic Minimal Surface) structures are advanced volumetric patterns used for lattices, porous media, and lightweight bulk regions. They can produce strong, printable microstructures but are computationally heavy.

---

## What is a TPMS in PyMFCAD?

In PyMFCAD, a TPMS is defined by a scalar field function $f(x, y, z)$ whose zero‑level surface defines the structure. You provide this function (or use a built‑in one) and PyMFCAD samples it into a volumetric shape.

---

## Step 1 — Define a TPMS function

You can define your own TPMS function and JIT‑compile it with `numba` for performance. Use `@njit` to speed up evaluation during voxelization.

```python
from numba import njit

@njit
def gyroid(x, y, z):
	return (
		(math.sin(x) * math.cos(y))
		+ (math.sin(y) * math.cos(z))
		+ (math.sin(z) * math.cos(x))
	)
```

**Why JIT?** TPMS sampling is called millions of times. Without `@njit`, it can be too slow to be practical.

---

## Step 2 — Build a TPMS shape

TPMS structures are typically used as **bulk**. Keep the geometry simple around it to reduce memory usage.

```python
# Pseudocode: use your TPMS function as the bulk
tpms = pymfcad.TPMS(
	size=(200, 200, 60),
	function=pymfcad.TPMS.gyroid,
	period=(20, 20, 20),
	threshold=0.0,
)

component.add_bulk("tpms_bulk", tpms, label="bulk")
```

---

## Limitations and performance pitfalls

TPMS generation is **memory‑intensive** and can crash large designs. The common failure modes are:

- Rendering runs out of RAM
- Slicing allocates huge intermediate grids
- Preview crashes on large TPMS volumes

---

## Ways to avoid crashes

### 1) Use a dedicated component with the TPMS as the only bulk

Keep the component minimal and make the TPMS the **only** bulk shape. This avoids complex boolean operations with other bulk solids and lets the slicer slice the TPMS cell once and tile that component.

### 2) Disable rendering of the component

When using large TPMS regions, disable rendering for that component:

```python
tpms_component = pymfcad.Component(
	size=(200, 200, 60),
	position=(0, 0, 0),
	px_size=0.0076,
	layer_size=0.01,
	hide_in_render=True,
)
```

This skips heavy render previews but still allows slicing.

---

## When to use TPMS

- Porous media structures
- Lightweight structural bulk
- Advanced mechanical or mixing behavior

---

Next: [Extra 6: Special Printing Techniques](e6-special_cases.md)
