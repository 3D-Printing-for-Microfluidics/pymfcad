# Reusable Components

Prev: [Part 7: Modeling Microfluidics](7-modeling-microfluidics.md)

This step introduces **reusable components**. The goal is to turn a feature (like a Y‑junction) into a class you can import and place in any device.

---

## What is a custom component?

A custom component is a Python class that inherits from `Component`. Inside `__init__`, you build geometry the same way you did in earlier steps—by adding bulk, voids, labels, and ports. The difference is that now your geometry is **encapsulated**, reusable, and parameterized.

---

## Example — Y‑junction mixer

We’ll build a minimal Y‑junction in small pieces, then provide a full copy‑paste version.

## Step 1 — Create a subclass and define geometry in `__init__`

Your class should:

- Subclass `Component`.
- Accept parameters you want to expose (sizes, margins, labels, etc.).
- Store init args/kwargs for equality checks (`self.init_args`, `self.init_kwargs`).
- Call `super().__init__()` with size, position, and resolution.

Use the same API you already know: `add_label`, `add_void`, and `add_bulk`.

### 1) Imports + class skeleton

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -0 +1 @@
+ import inspect
+ from pymfcad import Component, Port, Color, Cube, Polychannel, PolychannelShape
+ 
+class YJunctionMixer(Component):
+    """
+    Simple Y-junction mixer with two inlets and one outlet.
+    """
    </script>
</div>

### 2) Initialize and store parameters

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import inspect
 from pymfcad import Component, Port, Color, Cube, Polychannel, PolychannelShape
 
 class YJunctionMixer(Component):
     """
     Simple Y-junction mixer with two inlets and one outlet.
     """
+    def __init__(
+        self,
+        channel_size=(8, 8, 6),
+        channel_margin=(8, 8, 6),
+        px_size=0.0076,
+        layer_size=0.01,
+        quiet=False,
+    ):
+        frame = inspect.currentframe()
+        args, _, _, values = inspect.getargvalues(frame)
+        self.init_args = [values[arg] for arg in args if arg != "self"]
+        self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
+ 
+        super().__init__(
+            size=(
+                4 * channel_size[0],
+                2 * channel_size[1] + 3 * channel_margin[1],
+                channel_size[2] + 2 * channel_margin[2],
+            ),
+            position=(0, 0, 0),
+            px_size=px_size,
+            layer_size=layer_size,
+            quiet=quiet,
+        )
    </script>
</div>

### 3) Labels + bulk + channel voids

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -21 +21 @@
        super().__init__(
            size=(
                4 * channel_size[0],
                2 * channel_size[1] + 3 * channel_margin[1],
                channel_size[2] + 2 * channel_margin[2],
            ),
            position=(0, 0, 0),
            px_size=px_size,
            layer_size=layer_size,
            quiet=quiet,
        )
+ 
+        self.add_label("bulk", Color.from_name("aqua", 127))
+        self.add_label("void", Color.from_name("red", 255))
+
+        self.add_bulk(
+            "bulk_shape",
+            Cube(self._size, center=False),
+            label="bulk",
+        )
+
+        y_shape = Polychannel(
+            [
+                PolychannelShape(
+                    "cube",
+                    position=(0, channel_margin[1], channel_size[2]),
+                    size=(0, channel_size[1], channel_size[2]),
+                ),
+                PolychannelShape(
+                    "cube",
+                    position=(4 * channel_size[0], 1 * channel_margin[1], 0),
+                    size=(0, channel_size[1], channel_size[2]),
+                ),
+                PolychannelShape(
+                    "cube",
+                    position=(-4 * channel_size[0], 1 * channel_margin[1], 0),
+                    size=(0, channel_size[1], channel_size[2]),
+                ),
+            ]
+        )
+        y_shape.translate(
+            (
+                0,
+                channel_size[1] / 2,
+                channel_margin[2] / 2,
+            )
+        )
+        self.add_void("y_channel", y_shape, label="void")
    </script>
</div>

### 4) Instantiate and preview (before ports)

At this stage, instantiate the component and preview it **before** adding ports so you can validate the geometry alone.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -68 +68 @@
         self.add_void("y_channel", y_shape, label="void")
 
+if __name__ == "__main__":
+    YJunctionMixer().preview()
    </script>
</div>

![Y Junction](resources/8/8-1.png)

---

## Ports (what they are and why they matter)

**Ports are connection points** used by routing and device assembly. A port defines:

- **Type**: `IN`, `OUT`, or `INOUT`
- **Position**: where the port starts
- **Size**: channel size at that port
- **Normal**: the direction the port faces

Even before you learn routing, adding ports makes your component reusable and connectable.

### 5) Ports

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -68 +68 @@
         self.add_void("y_channel", y_shape, label="void")
+ 
+        self.add_port(
+            "inlet1",
+            Port(
+                Port.PortType.IN,
+                (0, channel_margin[1], channel_size[2]),
+                channel_size,
+                Port.SurfaceNormal.NEG_X,
+            ),
+        )
+        self.add_port(
+            "inlet2",
+            Port(
+                Port.PortType.IN,
+                (0, channel_size[1] + 2 * channel_margin[1], channel_size[2]),
+                channel_size,
+                Port.SurfaceNormal.NEG_X,
+            ),
+        )
+        self.add_port(
+            "outlet",
+            Port(
+                Port.PortType.OUT,
+                (
+                    4 * channel_size[0],
+                    channel_size[1] + channel_margin[1],
+                    channel_size[2],
+                ),
+                channel_size,
+                Port.SurfaceNormal.POS_X,
+            ),
+        )

 if __name__ == "__main__":
     YJunctionMixer().preview()
    </script>
</div>

### 6) Instantiate and preview (after ports)

Now instantiate and preview again **after** ports are added. This confirms the ports did not affect geometry and the component is ready for routing.

![Y Junction](resources/8/8-2.png)

---

## Full example

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import inspect
 from pymfcad import Component, Port, Color, Cube, Polychannel, PolychannelShape
 
class YJunctionMixer(Component):
     """
     Simple Y-junction mixer with two inlets and one outlet.
     """
     def __init__(
         self,
         channel_size=(8, 8, 6),
         channel_margin=(8, 8, 6),
         px_size=0.0076,
         layer_size=0.01,
         quiet=False,
     ):
         frame = inspect.currentframe()
         args, _, _, values = inspect.getargvalues(frame)
         self.init_args = [values[arg] for arg in args if arg != "self"]
         self.init_kwargs = {arg: values[arg] for arg in args if arg != "self"}
 
         super().__init__(
             size=(
                 4 * channel_size[0],
                 2 * channel_size[1] + 3 * channel_margin[1],
                 channel_size[2] + 2 * channel_margin[2],
             ),
             position=(0, 0, 0),
             px_size=px_size,
             layer_size=layer_size,
             quiet=quiet,
         )
 
         self.add_label("bulk", Color.from_name("aqua", 127))
         self.add_label("void", Color.from_name("red", 255))
 
         self.add_bulk(
             "bulk_shape",
             Cube(self._size, center=False),
             label="bulk",
         )
 
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
    </script>
</div>

---

## Notes

- Keep custom components in their own Python files so they’re easy to import.
- Use `self.init_args` / `self.init_kwargs` to make components comparable and cacheable.
- Ports make your component connectable for routing later.

---

## Next

Next: [Part 9: Routing with Fractional Paths](9-routing-fractional.md)
