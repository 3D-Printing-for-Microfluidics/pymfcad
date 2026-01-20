# Working with Polychannels
Prev: [Part 4: Creating Your First Component](4-building_first_component.md)

A **polychannel** is a high-level channel shape built from a sequence of simple shapes that are automatically hulled together. It is the easiest way to make smooth, variable-width channels.

Polychannels are powerful because they let you:

- Blend shapes (cube → rounded cube → sphere)
- Change cross‑section along the path
- Add rounded bends or smooth Bézier curves
- Mix absolute and relative positioning
- Build routing paths without manual boolean operations

---

## Step 1 — Import the polychannel classes

```python
from openmfd import Polychannel, PolychannelShape, BezierCurveShape
```

---

## Step 2 — Build a simple polychannel

Each `PolychannelShape` defines a point in the path. The channel is formed by hulling between these shapes.

```python
shapes = [
    PolychannelShape(
        shape_type="cube",
        position=(0, 0, 0),
        size=(0, 10, 10),
    ),
    PolychannelShape(
        shape_type="cube",
        position=(20, 0, 0),
        size=(10, 10, 10),
    ),
    PolychannelShape(
        shape_type="cube",
        position=(0, 20, 0),
        size=(10, 10, 10),
        corner_radius=5,
    ),
    PolychannelShape(
        shape_type="cube",
        position=(20, 20, 0),
        size=(10, 10, 10),
        corner_radius=0,
    ),
]

channel = Polychannel(shapes)
```

**Checkpoint:** You now have a smooth channel that turns a corner.

---

## Step 3 — Add the polychannel to a component

```python
from openmfd import Component, Color, Cube, Polychannel, PolychannelShape

component = Component(
    size=(100, 100, 20), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
)
component.add_label("default", Color.from_rgba((0, 255, 0, 255)))
component.add_label("bulk", Color.from_name("aqua", 127))

channel = [
    PolychannelShape(
        shape_type="cube",
        position=(0, 0, 0),
        size=(0, 10, 10),
    ),
    PolychannelShape(
        shape_type="cube",
        position=(20, 0, 0),
        size=(10, 10, 10),
    ),
    PolychannelShape(
        shape_type="cube",
        position=(0, 20, 0),
        size=(10, 10, 10),
        corner_radius=5,
    ),
    PolychannelShape(
        shape_type="cube",
        position=(20, 20, 0),
        size=(10, 10, 10),
        corner_radius=0,
    ),
]
component.add_void("polychannel_void", channel, label="default")

bulk_cube = Cube((100, 100, 20))
component.add_bulk("bulk", bulk_cube, label="bulk")

component.preview()
component.render("my_first_component.glb")
```

![Basic shapes](5-3.png)

## Step 4 — Add a Bézier curve (optional)

Use `BezierCurveShape` when you want a smooth, curved segment.

```python
from openmfd import Component, Color, Cube, Polychannel, PolychannelShape, BezierCurveShape

component = Component(
    size=(100, 100, 20), position=(0, 0, 0), px_size=0.0076, layer_size=0.01
)
component.add_label("default", Color.from_rgba((0, 255, 0, 255)))
component.add_label("bulk", Color.from_name("aqua", 127))

channel = Polychannel(
    [
        PolychannelShape(shape_type="cube", position=(0, 0, 0), size=(10, 10, 10)),
        PolychannelShape(shape_type="cube", position=(20, 0, 0), size=(10, 10, 10)),
        BezierCurveShape(
            control_points=[(50, 0, 0), (100, -100, 0), (200, 100, 0), (50, 0, 0)],
            bezier_segments=25,
            position=(50, 50, 0),
            size=(10, 10, 10),
            shape_type="rounded_cube",
            rounded_cube_radius=(3, 3, 3),
        ),
        PolychannelShape(
            shape_type="cube",
            position=(0, 50, 0),
            size=(10, 10, 10),
            corner_radius=0,
        ),
    ]
)
component.add_void("polychannel_void", channel, label="default")

bulk_cube = Cube((100, 100, 20))
component.add_bulk("bulk", bulk_cube, label="bulk")

component.preview()
component.render("my_first_component.glb")
```

![Basic shapes](5-4.png)

---

## Tips

- The first shape **cannot** be a Bézier curve.
- The first shape must define `shape_type`, `position`, and `size`.
- The last shape **cannot** have a non‑zero `corner_radius`.
- `corner_radius` applies at the bend point and stays active until reset to 0.
- `absolute_position=False` means each `position` is relative to the previous shape.
- `rounded_cube` requires `rounded_cube_radius`.
- All positions and sizes are in pixels/layers.
- You can mix cubes, spheres, and rounded cubes in the same channel.

---

## Capabilities and how to use them

- **Variable width/height:** change `size` from one shape to the next.
- **Rounded bends:** set `corner_radius` on the bend point, then reset to `0` later.
- **Smooth curves:** insert `BezierCurveShape` with `control_points`.
- **Shape blending:** mix `cube`, `sphere`, and `rounded_cube` to change channel profile.
- **Relative vs absolute positioning:** keep `absolute_position=False` for incremental steps, or set it to `True` for explicit coordinates.

---

Now that you have a basic understanding of polychannels, you can move on to adding components into your device.

## Next

Next: [Part 6: Integrating Subcomponents](6-subcomponents.md)