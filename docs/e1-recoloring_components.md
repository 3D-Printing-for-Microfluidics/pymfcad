# Customizing Labels and Colors
Prev: [Part 15: Slicing Process](15-slicing-process.md)

This section explains how to **relabel** shapes and labels so colors are consistent across a full device, including nested subcomponents.

Relabeling uses a single function:

`relabel(mapping, recursive=False)`

The `mapping` keys can be:

- a `Shape` instance
- a string name (shape name or label name)
- a fully qualified name (FQN) like `subcomponent.shape` or `subcomponent.label`

All new labels must exist in `component.labels` (use `add_label()` to create them first).

### Recursive relabeling

Set `recursive=True` to search beyond only the current level. If the key is a fully qualified name, relabeling first navigates to the lowest component in that FQN and then searches that component and its descendants for the key (shape name or label). If no FQN is provided, the search starts at the current component and traverses the full tree. This is useful when you want to update labels across nested subcomponents without using fully qualified names. Fully qualified names still work without `recursive=True`.

---

## Labels with prefixes (FQNs)

When a component is added as a subcomponent, all labels are **prefixed** with the subcomponent name.

Example:

- Original label: `control`
- Subcomponent name: `valve`
- Prefixed label: `valve.control`

This allows the visualizer to distinguish hierarchy levels. Relabeling is recursive; prefixed labels are replaced with the destination label.

---

## Examples

### Relabel a specific shape

```python
# Relabel a specific shape object
device.relabel({some_shape: "fluidic"})
```

### Relabel by shape name (current component)

```python
# Relabel a shape by its name in the current component
device.relabel({"channel_void": "fluidic"})
```

### Relabel by fully qualified shape name

```python
# Relabel a shape inside a subcomponent
device.relabel({"valve.channel_void": "control"})
```

### Relabel a label (all shapes with label)

```python
# Recursivly relabel a label (all pneumatics become controls)
device.relabel({"pneumatic": "control"}, recursive=True)
```

### Relabel by fully qualified label name

```python
# Relabel a prefixed label
device.relabel({"valve.pneumatic": "control"})
# Shapes labeled "valve.pneumatic" become "control"
```

### Relabel by fully qualified label name (recursive)
```python
# Relabel a prefixed label
device.relabel({"pump.pneumatic": "control"}, recursive=True)
# Shapes labeled "pump.pneumatic" become "control"
# Will also relabel any pneumatic below pump. i.e. pump.valve1.pneumatic
```

---

## Why relabel at all?

Relabeling makes multi‑component devices readable and consistent:

- All fluidic channels can share one color
- All pneumatic/control lines can share another
- You can override library defaults without editing the library code

This also makes debugging much easier.

---

Next: [Extra 2: Variable Layer Thickness Components](e2-variable_layer_thickness_components.md)
