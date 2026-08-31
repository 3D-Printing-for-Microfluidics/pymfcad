# Variable Layer Thickness Components
Prev: [Extra 1: Customizing Subcomponent Labels and Colors](e1-recoloring_components.md)

Variable layer thickness lets you define **different layer heights** within the same component. This is useful for membranes, thin features, or regions that need higher Z‑resolution.

PyMFCAD provides `VariableLayerThicknessComponent`, which behaves like `Component` but accepts a list of layer sizes.

---

## Step 1 — Create a variable‑layer component

You specify the overall size and a list of `(count, layer_size_mm)` tuples. The counts must sum to the component’s Z size (layer count).

```python
from pymfcad import VariableLayerThicknessComponent

component = VariableLayerThicknessComponent(
	size=(100, 100, 24),
	position=(0, 0, 0),
	px_size=0.0076,
	layer_sizes=[
		(6, 0.01),   # 6 layers at 10 um
		(4, 0.005),  # 4 layers at 5 um
		(14, 0.01),  # 14 layers at 10 um
	],
)
```

**Checkpoint:** The sum of layer counts (6+4+14=24) must equal the Z size.

---

## Step 2 — Build geometry as usual

Once created, you use the same APIs (`add_label`, `add_void`, `add_bulk`, etc.). The difference is how Z is discretized: use the **minimum common layer thickness** (the computed denominator) when specifying Z sizes or translations.

---

## How layer sizes are handled

- PyMFCAD computes a common denominator for modeling.
- This ensures correct geometry alignment across multiple layer sizes.
- For best results, component height should be an integer multiple of parent component layers.

---

## When to use this

- Thin membranes or diaphragms
- High‑resolution features in specific Z ranges
- Components that require mixed precision in Z

---

Next: [Extra 3: Workspaces](e3-workspaces.md)