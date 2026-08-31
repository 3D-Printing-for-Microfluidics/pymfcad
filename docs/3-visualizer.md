
# Using the Visualizer

Prev: [Part 2: Installation](2-installation.md)

PyMFCAD includes a browser‑based visualizer for inspecting and validating components. You will use it throughout the tutorial to confirm geometry, labeling, ports, and routing.

Goal: get comfortable navigating the preview so you can validate every step later.

## Step 1 — Launch the visualizer

From your project directory, run:

```bash
pymfcad
```

Or, if using uv:

```bash
uv run pymfcad
```

This command starts a local web server. If the page does not open automatically, go to [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser. Keep this terminal running while you preview models. To stop the server, press Enter in the terminal where it is running.

---

## Step 2 — General layout overview

The visualizer layout is organized around four main regions:

- **Toolbar** (bottom center) — common actions like snapshots and camera controls
- **View cube** (top right) — quick orientation with snapping to faces, edges, or corners
- **Model selector** (top right) — visibility and category controls for models and overlays
- **Auto Reload button** (bottom right) — enables or disables auto‑reloading of models

<img
    class="theme-aware-image"
    alt="Layout overview"
    src="resources/3/3-1_dark.png"
    data-light-src="resources/3/3-1_light.png"
    data-dark-src="resources/3/3-1_dark.png"
/>

---

## Step 3 — Keyboard and mouse controls

The visualizer supports two control styles: **Orbit** and **Trackball** (selectable in Settings → Camera). Common controls:

- **F11** — toggle fullscreen in the browser.
- **Double‑click** the model — set the camera target to the clicked surface (raycast to visible geometry).

### Orbit controls

- **Mouse**
	- Right‑click drag — orbit
	- Left‑click drag — pan
	- Scroll wheel / middle mouse — zoom
	- Hold **Shift** or **Ctrl** to swap orbit ↔ pan behavior
- **Keyboard**
	- Arrow keys — rotate
	- Arrow keys + **Shift** or **Ctrl** — pan

### Trackball controls

- **Mouse**
	- Right‑click drag — orbit
	- Left‑click drag — pan
	- Hold **A** to orbit, **S** to zoom, **D** to pan
- **Keyboard**
	- Arrow keys + **A** — orbit
	- Arrow keys + **S** — zoom (Up/Down) and roll (Left/Right)
	- Arrow keys + **D** — pan

---

## Step 4 — Model selector (overview)

The **Model Selector** controls visibility for the main geometry and overlays. Each group has a master toggle (Component) and may include sub‑toggles for specific content.

<img
    class="theme-aware-image"
    alt="Model selector"
    src="resources/3/3-2_dark.png"
    data-light-src="resources/3/3-2_light.png"
    data-dark-src="resources/3/3-2_dark.png"
/>

### Component

- **Component** — final bulk‑minus‑void geometry, used for export and slicing

<img
    class="theme-aware-image"
    alt="Component only"
    src="resources/3/3-3_dark.png"
    data-light-src="resources/3/3-3_light.png"
    data-dark-src="resources/3/3-3_dark.png"
/>

### Bounding box

- **Bounding Box** — black outline of the component bounds

<img
    class="theme-aware-image"
    alt="Bounding box only"
    src="resources/3/3-4_dark.png"
    data-light-src="resources/3/3-4_light.png"
    data-dark-src="resources/3/3-4_dark.png"
/>

### Unconnected ports

- **Unconnected Ports** — helper overlay showing unconnected port size, position, and type (green: IN, red: OUT, blue: IN/OUT)

<img
    class="theme-aware-image"
    alt="Ports only"
    src="resources/3/3-5_dark.png"
    data-light-src="resources/3/3-5_light.png"
    data-dark-src="resources/3/3-5_dark.png"
/>

### Bulk

- **Bulk** — all bulk shapes before void subtraction

<img
    class="theme-aware-image"
    alt="Bulk only"
    src="resources/3/3-6_dark.png"
    data-light-src="resources/3/3-6_light.png"
    data-dark-src="resources/3/3-6_dark.png"
/>

### Voids

- **Voids** — all void shapes

<img
    class="theme-aware-image"
    alt="Voids only"
    src="resources/3/3-7_dark.png"
    data-light-src="resources/3/3-7_light.png"
    data-dark-src="resources/3/3-7_dark.png"
/>

- **Fluidic Subcategory** — only voids labeled with fluidic for focused inspection


<img
    class="theme-aware-image"
    alt="Fluidic only"
    src="resources/3/3-8_dark.png"
    data-light-src="resources/3/3-8_light.png"
    data-dark-src="resources/3/3-8_dark.png"
/>

### Regional settings overlays

- **Regional** — visual overlays for regional settings (not part of final geometry)

<img
    class="theme-aware-image"
    alt="Regional only"
    src="resources/3/3-9_dark.png"
    data-light-src="resources/3/3-9_light.png"
    data-dark-src="resources/3/3-9_dark.png"
/>

---

## Step 5 — Toolbar (overview)

The **Toolbar** is divided into two sections: **Camera Controls** and **Tools**.

<img
    class="theme-aware-image"
    alt="Toolbar"
    src="resources/3/3-10_dark.png"
    data-light-src="resources/3/3-10_light.png"
    data-dark-src="resources/3/3-10_dark.png"
/>

### Camera controls

- **Home** — returns the camera to the home position and clears any selected saved camera position or animation frame (advanced topic).
- **Add saved camera position** — adds a new saved position.
	When a saved position is clicked, the camera moves to that viewpoint.

<img
    class="theme-aware-image"
    alt="Saved Camera Positions"
    src="resources/3/3-11_dark.png"
    data-light-src="resources/3/3-11_light.png"
    data-dark-src="resources/3/3-11_dark.png"
/>

- The active saved position can be updated with the current camera view by clicking the Update Camera button.

<img
    class="theme-aware-image"
    alt="Update Camera Positions"
    src="resources/3/3-12_dark.png"
    data-light-src="resources/3/3-12_light.png"
    data-dark-src="resources/3/3-12_dark.png"
/>

### Tools

- **Measurements** — opens measurment panel (covered later in [Extra 8: Advanced Visualizer Topics](e8-visualizer_advanced.md)).
- **Documentation** — opens the local version of this site.
- **Snapshot** — captures an image of the current view.
- **Animation** — advanced topic (covered later in [Extra 8: Advanced Visualizer Topics](e8-visualizer_advanced.md)).
- **Settings** — opens the settings panels.

---

## Step 6 — Settings panels (advanced topic)

The visualizer includes detailed settings panels for rendering and navigation. These are covered in [Extra 8: Advanced Visualizer Topics](e8-visualizer_advanced.md):

- **General settings**
- **Appearance settings**
- **Camera settings**
- **Light settings**

---

## Checkpoint

- You can open the Load Settings dialog and load a preview.
- You can identify the overview, toolbar, view cube, model selector, and reload controls.
- You understand the purpose of each model selector group.

With this overview, you should be ready to begin designing your own components.

Next: [Part 4a: Reading Code Examples](4a-reading-code-examples.md)