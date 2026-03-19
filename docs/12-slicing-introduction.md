# Slicing Introduction

Prev: [Part 11: Full Device Assembly](11-full-device.md)

Slicing converts a finished **bulk‑void device** into printer‑ready layers. It takes your rendered geometry plus print settings and produces a layer‑by‑layer representation the printer can execute.

Goal: understand what the slicer produces and how to verify the output.

---

## What slicing is

Slicing turns 3D geometry into a **stack of 2D layers**. Each layer becomes a grayscale image (one per print layer), and metadata is written so the printer knows exposure, timing, and positioning.

---

## Supported printers

Slicing is designed for **custom printers** that use our open‑source printing software, including our open‑source **OS1**. The output format is optimized for that ecosystem.

---

## What slicing outputs

The slicer writes a print bundle that typically includes:

- An **output folder** named after your filename (or a ZIP archive if you choose zipped output).
- A **JSON print file** that describes the job, settings, and per‑layer metadata.
- A **slices folder** containing 8‑bit grayscale images (one image per layer unless minimized).

Each slice image encodes exposure at that layer: black = no exposure, white = full exposure. If your workflow uses multiple exposures per layer (e.g., membranes or secondary doses), you may see multiple images referenced from the JSON.

If you want a human‑readable walkthrough of the JSON fields, see the [JSON Print File Reference](r4-json_print_file_reference.md).

---

## Checkpoint

- You understand what files the slicer will generate.
- You know where to look for the JSON print file details.

---

## Next

Next: [Part 13: Slicing Settings](13-slicing-settings.md)
