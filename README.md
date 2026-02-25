# OpenMFD

OpenMFD is a Python package for rapid design and prototyping of 3D-printed microfluidic devices. It provides a component-based workflow for building reusable parts, assembling devices, routing connections, visualizing results, and generating printer-ready slices.

## Key features

- **Component-based design:** Build devices from reusable components and subcomponents.
- **Flexible geometry:** Create primitives, complex shapes, polychannels, and Bézier curves.
- **Pixel/layer precision:** Work at printer resolution for high-fidelity fabrication.
- **Automatic routing:** Connect ports with manual or fully automatic routing tools.
- **Visualization + rendering:** Preview designs in 3D before slicing.
- **Slicing support:** Export printer-ready slices (for custom printers only).
- **Extensible:** Add your own component libraries and reusable features.

## Typical workflow

1. Define components (bulk material + negative feature)
2. Assemble devices (position and combine components)
3. Route connections (ports + routing tools)
4. Visualize and render (inspect in 3D)
5. Slice and export (generate print files)

## Installation

```bash
pip install openmfd
```

## Quick start

See the documentation for a full, step-by-step tutorial and API reference:

- Documentation: https://openmfd.readthedocs.io
- Repository: https://github.com/3D-Printing-for-Microfluidics/openmfd

## Who is this for?

OpenMFD is ideal for researchers, engineers, and educators working on microfluidics, lab-on-a-chip devices, and rapid prototyping with high-resolution 3D printers.
