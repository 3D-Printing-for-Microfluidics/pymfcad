# JSON Print File Reference

This reference explains the JSON print file produced by OpenMFD in plain language. It is based on our open source print file schema and designed to be readable without the full schema document.

**Source of truth:** A public schema repository exists at [https://github.com/3D-Printing-for-Microfluidics/3D_printer_json_print_file](https://github.com/3D-Printing-for-Microfluidics/3D_printer_json_print_file).

---

## Overview: what this file represents

The JSON file is the **print job definition** for a single device. It contains:

- **Metadata** about the design and printer
- **Default layer settings** that apply everywhere
- **Optional per-layer overrides**
- **References** to image files used for exposure
- **Optional special techniques** (vacuum, squeeze, zero‑micron layers, print‑on‑film)

Think of it as a recipe: defaults at the top, exceptions at the layer level.

---

## Top-level sections

### `Header`

Global file info and where to find the slice images.

**Key fields**

- `Schema version`: version of the schema used to validate this file
- `Image directory`: relative folder containing the slices (usually `slices`)
- `Comment` (optional)

### `Design`

Human-facing metadata. This is not required for printing, but it is essential for traceability.

**Common fields**

- `User`, `Purpose`, `Description`
- `Resin`, `3D printer`, `Slicer`, `Date`
- `Design file`, `STL file` (optional)

### `Default layer settings`

The global defaults applied to every layer unless overridden later.

**Contains**

- `Position settings`: motion profile (lift, wait, speed)
- `Image settings`: exposure profile (exposure time, power, wavelength)
- `Number of duplications`: how many times to repeat the layer
- `Comment` (optional)

### `Layers`

The `Layers` array is **required**. Each entry represents a layer in the print stack. Overrides within a layer are optional, but the layer entries themselves must exist.

If a layer entry includes overrides, it can replace **position settings**, **image settings list**, and **duplication count** for that layer.

Layers can also reference a **named layer group** using `Using named layer group`.

Use overrides for:

- burn-in (longer early exposures)
- membrane steps
- selective dose changes above features

## Position settings (motion)

These fields control the mechanics between layers:

- `Layer thickness (um)`: thickness of this layer in micrometers
- `Distance up (mm)`: lift distance after exposure
- `BP up speed (mm/sec)` / `BP down speed (mm/sec)`
- `BP up acceleration (mm/sec^2)` / `BP down acceleration (mm/sec^2)`
- `Initial wait (ms)`, `Up wait (ms)`, `Final wait (ms)`
- `Using named position settings` (optional)
- `Special layer techniques` (optional)
	- `Squeeze out resin`

**When to override:** if a layer needs a different motion profile (e.g., membrane formation or thick layers).

---

## Image settings (exposure)

These fields control light exposure per layer:

- `Image file`: filename of the slice image
- `Do grayscale correction`: grayscale irradiance correction
- `Image x offset (um)` / `Image y offset (um)`: image offsets in micrometers
- `Layer exposure time (ms)`: exposure duration
- `Light engine` and `Light engine power setting`
- `Light engine wavelength (nm)`
- `Relative focus position (um)`
- `Wait before exposure (ms)`, `Wait after exposure (ms)`
- `Using named image settings` (optional)
- `Special image techniques` (optional)
	- `0 um layer`
	- `Print on film`

**When to override:** if a region needs extra dose, or if using multi-exposure steps.

**Important:** If you do not specify an image name for a layer, the slicer will use the default image (the first image).

### Image settings list

Layers store one or more exposures under `Image settings list`. This enables multiple exposures per layer (membranes, secondary dose, or special techniques).

You can set `Using named default image settings` at the layer level to apply a named image settings preset as a base for all exposures in that layer.

---

## Special print techniques (advanced)

At the top level, OpenMFD can write:

- `Special print techniques`
	- `Print under vacuum`

These are optional and only appear if enabled in settings.

---

## Named settings and templates (advanced)

The schema supports named settings and templates to reduce repetition. If you see:

- `Named position settings`
- `Named image settings`
- `Named layer groups`

…these are reusable presets referenced by layers. They are optional and generally used in advanced workflows. OpenMFD uses named position and image settings.

---

### Variables (advanced)

You can define `Variables` at the top level and reuse them throughout the JSON using `${...}` expressions. Our custom 3D printers evaluates these with `simple_eval`. These are not curently used by OpenMFD.

- Syntax: `${expression}`
- Example: `${layer * 10}`

This is useful for compact, readable parameter sweeps or derived values across many layers.

---

## Practical validation checklist

- `Header.Image directory` points to the correct slices folder
- Default settings are present and sensible
- Any per-layer overrides are intentional

---

## Notes on grayscale

Slice images are 8-bit grayscale:

- 0 = no exposure
- 255 = full exposure
- intermediate values = partial dose (not currently used)

OpenMFD can also express multi-exposure workflows by listing multiple images per layer in the JSON.
