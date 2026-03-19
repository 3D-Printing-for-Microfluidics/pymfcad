# Introduction

PyMFCAD is a Python package for rapidly designing and fabricating 3D‑printed microfluidic devices. It targets DLP‑SLA 3D printing workflows while remaining accessible to anyone who wants to prototype microfluidic systems with modern additive manufacturing.

This guide is a **step‑by‑step learning path**. Each part builds on earlier concepts so you can progress from first principles to a complete, printable device. The API reference is kept separate so the tutorial can stay focused and beginner‑friendly.

## How to use this guide

- Follow the steps in order; each part depends on the last.
- Run the example code as you go to validate geometry and settings.
- Use the visualizer early and often to catch issues before slicing.

## Prerequisites

- Python 3.10+ and basic Python scripting comfort
- Knowledge of your printer’s pixel size and layer thickness
- A basic understanding of DLP‑SLA 3D printing (exposure, layers)

## Key features

- **Component‑based design:** Build microfluidic models—called "devices"—from reusable parts (components and subcomponents) to share and standardize designs.
- **Flexible geometry:** Create and combine shapes such as cubes, spheres, rounded cubes, and text extrusions. Advanced structures like polychannels and Bézier curves are also easily accessible.
- **Pixel/layer precision:** Specify geometry in pixels and layers to match DLP‑SLA 3D print resolution.
- **Routing tools:** Connect ports and features using manual or automatic routing for complex layouts.
- **Interactive visualization:** Preview designs, validate labels and ports, and export for fabrication.
- **Slicing support:** Generate printer‑ready slices (optimized for custom DLP‑SLA workflows).
- **Extensible:** Import external component libraries or build your own.

## Typical workflow

1. **Define components:** Create basic building blocks using shapes and labels.
2. **Assemble devices:** Combine components and subcomponents, positioning and transforming as needed.
3. **Add connections:** Use routing tools to connect ports and features.
4. **Preview and validate:** Inspect geometry, labels, and ports before fabrication.
5. **Slice and print:** Generate printer‑ready outputs for your DLP‑SLA process.

## Mental model (30‑second version)

- **Component**: a reusable block made of **bulk** material (solid) and negative **voids** (channels).
- **Device**: a printable assembly bound to a printer’s pixel/layer resolution.
- **Labels**: named color groups used to organize geometry and visualization.
- **Ports + routing**: define and connect fluidic interfaces between components.
- **Slicer**: converts the device into a JSON print job plus an image stack.

You will gain a greater understanding of this mental model throughout the tutorial.

## What you will learn

By the end of Part 15, you will be able to:

- Design and preview components
- Assemble devices and connect ports
- Configure slicing settings
- Generate print files and inspect outputs
- Apply regional settings (membranes, secondary dose, etc.)

## Who should use PyMFCAD?

PyMFCAD is ideal for:

- Researchers developing new microfluidic devices
- Engineers prototyping lab‑on‑a‑chip systems
- Educators teaching microfluidics or digital fabrication
- Anyone interested in rapid, reproducible microfluidic design

Whether you are new to microfluidics or an experienced designer, PyMFCAD provides a powerful, scriptable environment to accelerate your work.

---

Next: [Part 2: Installation](2-installation.md)
