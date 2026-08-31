# Stitching Devices
Prev: [Extra 3: Workspaces](e3-workspaces.md)

Stitching is used when a device is **larger than a single light engine field of view**. Instead of printing as a single exposure, stitching divides the device into a grid of tiles, each positioned and exposed separately but seamlessly combined on the build platform.

Stitching is achieved by **setting up workspaces with stitching parameters** that control how multiple light engine positions are combined into a single virtual larger region.

---

## How stitching works

1. **Define a device** whose pixel dimensions fit your needs
2. **Create a workspace** with stitching parameters that specify the tile grid (e.g., 2×2, 3×2).
3. **Slice the workspace** to generate an $n \times m$ grid of exposures, each with its own image offset.
4. **Print the job** — the printer's XY stage positions each tile, and they are exposed in sequence or as specified in the print file.

Each tile uses the same image stack but with different `Image x offset (um)` and `Image y offset (um)` in the JSON output, allowing the projector to print adjacent regions that seamlessly stitch together.

---

## Basic stitching workflow

Define a component

```python
from pymfcad import Component, Cube, Color

component = Component(
	size=(5120, 3200, 200),
	layer_size=0.01,
	px_size=0.0076,
)

component.add_label("bulk", Color.from_name("gray", 127))
component.add_bulk("bulk", Cube(component._size, center=False), label="bulk")
```

Then create a workspace with desired stitching parameters:

```python
from pymfcad import Workspace, Printer

# Load or create a printer definition
printer = Printer.from_file("printer_config.json")

workspace = Workspace(
	printer=printer,
	pixel_size=0.0076,
	exposure_abs_pos_um=(0, 0),  # Build platform position for this exposure
	light_engine_stitching=(2, 2),  # 2×2 tile grid
)

# Slice the workspace with your component
generator = PrintFileGenerator(workspaces=[workspace], ...)
```

---

## Light engine settings and stitching constraints

The **light engine settings object** defines hardware-level parameters that constrain how stitching can be configured:

- **Pixel overlap (`px_overlap`)**: The number of overlapping pixels between adjacent tiles. This is set by the light engine calibration and is used to blend seamlessly between tiles.
- **Projection position limits (`x_offset_limits`, `y_offset_limits`)**: The minimum and maximum XY position (in micrometers) that the projector can position on the build platform. These limits define the **maximum number of tiles** that can be stitched in each direction.

For example, if a light engine has:
- Projection field: 2560 × 1600 pixels at 7.6 µm/pixel ≈ 19.5 × 12.2 mm
- Projection position range: ±20 mm in X, ±15 mm in Y
- Pixel overlap: 8 pixels for seamless blending

Then you can stitch tiles across this projection range. Requesting more tiles than the hardware allows will fail validation.

The stitching parameters you provide in the workspace must respect these light engine constraints. The pixel overlap and position limits are automatically applied during slicing to validate and generate the proper image offsets.

---

## Stitching without workspaces

You can slice a device without workspaces for basic stitching, but **workspaces enable advanced control**:

- **Multiple devices**: Print different devices at different positions in a single job
- **Flexible stitching parameters**: Adjust tile counts and overlap on-the-fly
- **Custom positioning**: Place stitched regions anywhere on the build platform

---

## Requirements

- The printer **must have an XY stage** for stitched printing
- Light engine positions must be properly calibrated for seamless stitching
- Overlap regions (if used) should be chosen to ensure strong bonding between tiles

---

## When to use stitching

- Devices larger than a single projector field of view
- Multi‑tile chips that require XY stage movements
- Scenarios where you need precise control over tile positioning and overlap

---

Next: [Extra 5: Embedding Devices](e5-embedding.md)

