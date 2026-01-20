# Designing Custom Subcomponents
Prev: [Part 7: Routing](7-routing.md)

Designing your own subcomponents in OpenMFD is straightforward. You create a new class that inherits from `Component`, define geometry in `__init__`, and use `self.` for all operations. This lets you encapsulate reusable device features like mixers, valves, or junctions.

Use the template here: [Custom Component Template](r3-component_template.md).

---

## Step 1 — Create a custom class

Subcomponents should subclass `Component` (or `VariableLayerThicknessComponent` when needed).

Key requirements:

- Implement `__init__` with parameters you want to expose.
- Save constructor arguments in `self.init_args` and `self.init_kwargs`.
- Call `super().__init__()` with size, position, and resolution.

---

## Step 2 — Define geometry and ports

Inside `__init__`, use `self.add_label`, `self.add_void`, `self.add_bulk`, `self.add_port`, `self.add_subcomponent`, or any other Component function to define the subcomponent.

---

## Step 3 — Save it as a reusable module

Place your class in a standalone Python file so you can import it in any project.

---


## Example — Y‑junction subcomponent
Below is a minimal example of a Y-junction mixer subcomponent:

```python
import inspect
from openmfd import Component, Port, Color, Cube, Polychannel, PolychannelShape

class YJunctionMixer(Component):
    """
    Simple Y-junction mixer with two inlets and one outlet.
    """

    def __init__(self, channel_size=(8, 8, 6), channel_margin=(8, 8, 6)):
        # Store constructor arguments for equality comparison.
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        self.init_args = [values[arg] for arg in args if arg != "self"]
        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}

        # Initialize the base Component
        super().__init__(
            size=(
                4 * channel_size[0],
                2 * channel_size[1] + 3 * channel_margin[1],
                channel_size[2] + 2 * channel_margin[2],
            ),
            position=(0, 0, 0),
            px_size=0.0076,
            layer_size=0.01,
        )

        self.add_label("bulk", Color.from_name("gray", 255))
        self.add_label("void", Color.from_name("aqua", 255))

        # Add a simple Y-shaped channel using Polychannel
        y_shape = Polychannel(
            [
                PolychannelShape(
                    "cube",
                    position=(0, channel_margin[1], channel_size[2]),
                    size=(0, channel_size[1], channel_size[2]),
                ),
                PolychannelShape(
                    "cube",
                    position=(4 * channel_size[0], 1 * channel_margin[1], 0),
                    size=(0, channel_size[1], channel_size[2]),
                ),
                PolychannelShape(
                    "cube",
                    position=(-4 * channel_size[0], 1 * channel_margin[1], 0),
                    size=(0, channel_size[1], channel_size[2]),
                ),
            ]
        )
        y_shape.translate(
            (
                0,
                channel_size[1] / 2,
                channel_margin[2] / 2,
            )
        )
        self.add_void("y_channel", y_shape, label="void")

        self.add_bulk(
            "BulkShape",
            Cube(self._size, center=False),
            label="bulk",
        )

        # Add ports: two inlets and one outlet
        self.add_port(
            "inlet1",
            Port(
                Port.PortType.IN,
                (0, channel_margin[1], channel_size[2]),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "inlet2",
            Port(
                Port.PortType.IN,
                (0, channel_size[1] + 2 * channel_margin[1], channel_size[2]),
                channel_size,
                Port.SurfaceNormal.NEG_X,
            ),
        )
        self.add_port(
            "outlet",
            Port(
                Port.PortType.OUT,
                (
                    4 * channel_size[0],
                    channel_size[1] + channel_margin[1],
                    channel_size[2],
                ),
                channel_size,
                Port.SurfaceNormal.POS_X,
            ),
        )


if __name__ == "__main__":
    YJunctionMixer().preview()

```

![Y Junction](8.png)

This pattern can be adapted for any custom subcomponent. Define your geometry and ports inside the class, then import and reuse it across devices.

**Checkpoint:** In the visualizer, you should see a Y‑shaped channel inside a rectangular bulk.

Next: [Part 9: Creating Your First Slicable Device](9-slicer_settings.md)