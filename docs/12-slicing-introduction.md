# Slicing Introduction

Prev: [Part 11: Full Device Assembly](11-full-device.md)

The process of converting a component into a print file is often refered to as slicing a model. For the purpose of this documentation, we will use this terminology. Slicing converts a finished **bulk‑void component** into printer‑ready layers. It takes your rendered geometry plus printer, resin, and print settings and produces a layer‑by‑layer representation the printer can execute.

Goal: understand what `PrintFileGenerator` produces and how to verify the output.

---

## What is slicing

Slicing turns 3D geometry into a **stack of 2D layers**. Each layer becomes one or more grayscale images. Metadata is also generated for each image so the printer knows exposure, timing, and positioning.

---

## Supported printers

Our slicing architechture is designed for **custom printers** that use our open‑source printing software, including our open‑source **OS1**. The output format is optimized for that ecosystem. Predefined printer and resin profiles are available in the printer and resin libraries; Part 13 shows how to use them.

To slice devices for other printers, it is recommended you export the 3D model and use their recommended slicer, as such, you do not need to complete this section of the tutorial. 

Advanced coders may choose to contribute by adding additional printer support to the code base; although it is important to note that other printers **will not** support the full PyMFCAD feature set (i.e. multiple images per layer, varying exposure and movement parameters per layer, advanced techniques, etc).

---

## What slicing outputs

`PrintFileGenerator` writes a print bundle that typically includes:

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
