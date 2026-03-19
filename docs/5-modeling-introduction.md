# Modeling Introduction

Prev: [Part 4: Creating Your First Component](4-building_first_component.md)

This short bridge introduces the **modeling mindset** you’ll use in the next steps. It explains what modeling means in PyMFCAD and how your design choices map to DLP‑SLA printing.

Goal: understand the core modeling concepts before building full devices.

---

## The core mental model

- You start with **bulk** (solid material) and carve out **voids** (channels).
- The final device is always **bulk minus voids**.
- Everything is designed on a **pixel/layer grid**, not continuous millimeters.

This mirrors how DLP‑SLA printers work: each layer is an image, and each pixel/layer is the smallest printable unit.

---

## Coordinate system and units

- **X/Y** are in **pixels** (projector pixels).
- **Z** is in **layers** (stacked exposures).
- `px_size` and `layer_size` define the physical size of each unit in mm.

If you design in mm, convert to pixels/layers before modeling so features align with the printer grid. (desired mm measurement divided by layer height for Z or pixel size for X/Y in mm)

---

## Shapes, transforms, and operations

You will construct geometry from a small set of shapes (cubes, cylinders, spheres, rounded cubes) and then:

- **Transform** them (translate, rotate, mirror)
- **Combine** them (union / addition)
- **Reuse** them (copy and parameterize)

This keeps designs compact and readable while enabling parametric changes later.

---

## Labels and ports (why they matter early)

- **Labels** are color groups that make geometry readable in the visualizer and later in slicing.
- **Ports** are named connection points that routing uses to connect components.

Even in simple models, adding labels and ports early prevents confusion as designs grow.

---

## What you’ll do next

In the next step you’ll build basic bulks and voids, explore the shape gallery, and practice combining geometry. After that, you’ll connect features into real microfluidic structures.

---

## Next

Next: [Part 6: Modeling — Bulks, Voids, and Shapes](6-modeling-bulks-voids-shapes.md)
