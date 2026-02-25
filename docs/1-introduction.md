# Introduction


OpenMFD is a Python package for the rapid design and prototyping of 3D-printed microfluidic devices. It is designed for researchers, engineers, and anyone interested in building complex microfluidic systems using modern additive manufacturing techniques.

This guide is a **step-by-step learning path**. It focuses on concepts and workflows first, with the API reference as a separate resource.

## Key Features

- **Component-based design:** Build devices from reusable, modular parts (components and subcomponents), making it easy to share and standardize designs.
- **Flexible geometry:** Create a wide range of shapes, including cubes, spheres, rounded cubes, text extrusions, and advanced structures like polychannels and Bézier curves.
- **Pixel/layer precision:** All designs are specified in pixels and layers, matching the resolution of high-end 3D printers for maximum fidelity.
- **Automatic routing:** Tools for connecting ports and features with fully automatic or manual routing, supporting complex device layouts.
- **Rendering and visualization:** Preview your designs interactively before printing, and export to standard 3D formats for further processing or slicing.
- **Slicing support:** Convert your designs into printer-ready slices (currently optimized for custom 3D printers).
- **Extensible:** Import community or custom component libraries, and create your own reusable features.

## Typical Workflow

1. **Define components:** Create basic building blocks using shapes and labels.
2. **Assemble devices:** Combine components and subcomponents into complete devices, positioning and transforming as needed.
3. **Add connections:** Use routing tools to connect ports and features.
4. **Preview and render:** Visualize your device in 3D, check for errors, and export models.
5. **Slice and print:** Generate printer-ready files for fabrication.

## Mental Model (30‑second version)

- **Component**: a reusable block made of **bulk** material (solid) and negative features/**voids** (channels).
- **Device**: a printable assembly tied to a printer’s resolution.
- **Labels**: named colors used to group geometry and settings for visualization purposes.
- **Ports + routing**: define connections between components.
- **Slicer**: turns the device into a JSON print job + image stack.

You will build up this model gradually throughout the tutorial.

## What you will learn

By the end of Part 14, you will be able to:

- Design and preview components
- Assemble devices and connect ports
- Configure slicing settings
- Generate print files and inspect outputs
- Apply regional settings (membranes, secondary dose, etc.)

## Who Should Use OpenMFD?

OpenMFD is ideal for:

- Researchers developing new microfluidic devices
- Engineers prototyping lab-on-a-chip systems
- Educators teaching microfluidics or digital fabrication
- Anyone interested in rapid, reproducible microfluidic design

Whether you are new to microfluidics or an experienced designer, OpenMFD provides a powerful, scriptable environment to accelerate your work.

---

Next: [Part 2: Installation](2-installation.md)
