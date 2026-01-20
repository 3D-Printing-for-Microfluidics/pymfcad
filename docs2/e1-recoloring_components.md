# Customizing Subcomponent Labels and Colors
Prev: [Part 12: Configuring Regional Settings](12-regional_settings.md)

This section explains how to **relabel** subcomponents and shapes so they share consistent colors and labels across a full device.

OpenMFD provides three relabeling tools:

1. `relabel_subcomponents(...)`
2. `relabel_labels(...)`
3. `relabel_shapes(...)`

They solve different problems. Use the simplest one that matches your use case.

---

## 1) `relabel_subcomponents(...)`

**Use when:** You want to recolor **entire subcomponents** (all their labels and shapes) to a single target label.

**Why:** This is the fastest way to standardize a library component under a single device-level label (e.g., make all pneumatics red).

```python
# Make all shapes inside the listed subcomponents use the "control" label
device.relabel_subcomponents([valve, pump], "control")
```

---

## 2) `relabel_labels(...)`

**Use when:** You want to replace **specific label names** (possibly across nested subcomponents) with a new label.

**Why:** This is the most flexible way to standardize labeling without flattening everything into one label.

```python
# Replace any existing "pneumatic" labels with "control" (recursive by default)
device.relabel_labels(["pneumatic"], "control")
```

Notes:

- This can be applied recursively across subcomponents.
- It preserves structure but updates colors and label names.

---

## 3) `relabel_shapes(...)`

**Use when:** You want to recolor **specific shapes only** (e.g., a single void or region).

**Why:** This is the most precise tool. Use it when only a few shapes need to change.

```python
# Relabel only a specific set of shapes
device.relabel_shapes([some_shape, other_shape], "fluidic")
```

---

## Choosing the right approach

- **Whole subcomponent → one label:** use `relabel_subcomponents`
- **Replace label names globally:** use `relabel_labels`
- **Target a few shapes:** use `relabel_shapes`

---

## Why relabel at all?

Relabeling makes multi‑component devices readable and consistent:

- All fluidic channels can share one color
- All pneumatic/control lines can share another
- You can override library defaults without editing the library code

This also makes slice previews and debugging much easier.

---

Next: [Extra 2: Variable Layer Thickness Components](e2-variable_layer_thickness_components.md)
