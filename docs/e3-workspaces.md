## Workspaces

Prev: [Extra 2: Variable Layer Thickness Components](e2-variable_layer_thickness_components.md)

---

## What are PrintFileGenerator Workspaces

A **workspace** represents a physical light engine position within a print job. It is defined by:

- **Pixel size (`px`)**: Determines the light engine to be used via lookup
- **Origin**: The location where the light engine is centered on the build platform
- **Stitching parameters**: Optional parameters that combine multiple light engine positions into one virtual larger region

Each workspace controls exactly one exposure and positioning setup. The pixel size dictates which light engine is used, and the origin determines where that exposure appears on the build platform. When stitching parameters are provided, the workspace can extend across multiple adjacent light engine positions to create a seamlessly larger projection area.

### Why use workspaces?

Workspaces give you **exact control over printer behavior**. This enables powerful workflows:

**Single workspace:**
- Print multiple components at the same time.
- Position components **anywhere within the projection region** of the light engine
- Position the **projection region anywhere on the build platform**
- Precise spatial control over a single exposure

**Multiple workspaces:**
- Print **multiple components across different positions** on the build platform
- Each component is **positioned independently** within its light engine
- **Stitching**: Use stitching parameters to combine adjacent light engine positions into a single virtual region, enabling larger print areas and custom geometry layouts
- Mix components at different pixel sizes and build platform locations in a single print job

Workspaces are a powerful tool for advanced power users who need precise control over how multiple components are positioned, exposed, and combined during printing.

---

## Checkpoint

- You understand what a workspace is and why it's useful for advanced workflows
- You know that workspaces manage layer-by-layer component assembly
- You're ready to explore stitching and embedding

---

## Next

Next: [Extra 4: Stitching Devices](e4-stitching.md)