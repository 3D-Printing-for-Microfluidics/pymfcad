# Creating Your First Component

Prev: [Part 3: Using the Visualizer](3-visualizer.md)

This step shows the core building blocks of OpenMFD: **components**, **labels**, **shapes**, and **operations**. We’ll build a simple component and preview it.

---

## Step 1 — Import OpenMFD

```python
import openmfd
```

---

## Step 2 — Create a component

Components are sized in **pixels (x/y)** and **layers (z)**. You also define the physical resolution: `px_size` and `layer_size` in mm.

```python
component = openmfd.Component(
	size=(100, 100, 20),
	position=(0, 0, 0),
	px_size=0.0076,
	layer_size=0.01,
)
```

**Checkpoint:** You now have an empty component with a defined size and resolution.

---

## Step 3 — Add labels (colors)

Labels are **named color groups**. Every shape you add must reference a label. Labels are used for visualization and for grouping features.

Rules:

- Label names must be valid Python identifiers (no spaces, must start with a letter).
- Each label has a `Color`.

```python
component.add_label("default", openmfd.Color.from_rgba((0, 255, 0, 255)))
component.add_label("bulk", openmfd.Color.from_name("aqua", 127))
```

Common color constructors:

- `Color.from_rgba((r, g, b, a))`
- `Color.from_rgba_percent((r, g, b, a))`
- `Color.from_hex("FFFFFF", a)`
- `Color.from_name("aqua", a)`

A list of supported named colors can be found [here](r2-color.md).

**Checkpoint:** Your component has two label groups: `default` and `bulk`.

---

## Step 4 — Understand shapes and operations

OpenMFD provides basic primitives:

- `Cube`, `Cylinder`, `Sphere`, `RoundedCube`
- `TextExtrusion`, `ImportModel`, `TPMS`

Every shape can be transformed:

- `translate((x, y, z))`
- `rotate((rx, ry, rz))`
- `resize((x, y, z))`
- `mirror((x, y, z))`

And combined with boolean operations:

- **Union:** `a + b`
- **Difference:** `a - b`
- **Hull:** `a.hull(b)`
- **Copy:** `a.copy()`

You will use these to build complex channel geometry from simple blocks.

---

## Step 5 — Add void shapes (channels)

Void shapes represent **empty space** (channels). These are subtracted from the bulk.

```python
cube = openmfd.Cube((10, 10, 10))
component.add_void("first_cube", cube, label="default")

sphere = openmfd.Sphere((10, 10, 7)).translate((100, 100, 20))
component.add_void("my_sphere", sphere, label="default")

hello = openmfd.TextExtrusion("Hello World!", height=1, font_size=15)
hello.translate((0, 0, 19))
component.add_void("hello", hello, label="default")
```

---

## Step 6 — Add bulk (solid material)

Every component must include **at least one bulk shape**. Bulk is the solid material that voids are carved out of.

**Best practice:** add bulk shapes **last** to avoid render glitches.

```python
bulk_cube = openmfd.Cube((100, 100, 20))
component.add_bulk("bulk", bulk_cube, label="bulk")
```

---

## Step 7 — Preview the component

```python
component.preview()
```

**Checkpoint:** In the visualizer you should see a solid block with the void shapes removed.

![visualizer-difference](4-1.png)

Toggle **Bulk** and **Void** to see each category separately:

![visualizer-bulk](4-2.png)

![visualizer-bulk](4-3.png)

---

## Step 8 — Render a GLB (optional)

```python
component.render("my_first_component.glb")
```

This saves a GLB file to your current working directory.

---

## Next

In the next tutorial, we will explore a more flexible shape type: polychannels.

Next: [Part 5: Working with Polychannels](5-polychannel.md)

