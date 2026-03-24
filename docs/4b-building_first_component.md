# Creating Your First Component

Prev: [Part 4a: Reading Code Examples](4a-reading-code-examples.md)

This quick “hello world” tutorial builds a minimal component and previews it in the visualizer.

You don’t need to understand the code yet—we’ll explain what each part does in later sections. The goal here is simply to create your first file and confirm that everything is working end‑to‑end.

Goal: create a component, label it, and confirm that it renders.

---

## Step 1 — Import PyMFCAD

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -0 +1 @@
+import pymfcad
    </script>
</div>

---

## Step 2 — Create a component

Components are sized in **pixels (x/y)** and **layers (z)**. You also define the physical resolution with `px_size` and `layer_size` (mm).

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 import pymfcad
+
+component = pymfcad.Component(
+    size=(120, 40, 10), # X pixel count, Y pixel count, Z layer count
+    position=(0, 0, 0),
+    px_size=0.0076,
+    layer_size=0.01,
+)
    </script>
</div>

---

## Step 3 — Add labels

Labels are named color groups used for visualization and organization.

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -3 +3 @@
 component = pymfcad.Component(
     size=(120, 40, 10), # X pixel count, Y pixel count, Z layer count
     position=(0, 0, 0),
     px_size=0.0076,
     layer_size=0.01,
 )
+
+component.add_label("default", pymfcad.Color.from_rgba((0, 255, 0, 255)))
+component.add_label("bulk", pymfcad.Color.from_name("aqua", 127))
    </script>
</div>

---

## Step 4 — Add a simple void

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -10 +10 @@
 component.add_label("default", pymfcad.Color.from_rgba((0, 255, 0, 255)))
 component.add_label("bulk", pymfcad.Color.from_name("aqua", 127))
+
+hello = pymfcad.TextExtrusion("Hello World!", height=1, font_size=15)
+hello.translate((5, 5, 9))
+component.add_void("hello", hello, label="default")
    </script>
</div>

---

## Step 5 — Add bulk

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -13 +13 @@
 hello = pymfcad.TextExtrusion("Hello World!", height=1, font_size=15)
 hello.translate((5, 5, 9))
 component.add_void("hello", hello, label="default")
+
+bulk_cube = pymfcad.Cube((120, 40, 10))
+component.add_bulk("bulk_shape", bulk_cube, label="bulk")
    </script>
</div>
---

## Step 6 — Preview

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -17 +17 @@
 bulk_cube = pymfcad.Cube((120, 40, 10))
 component.add_bulk("bulk_shape", bulk_cube, label="bulk")
+
+component.preview()
    </script>
</div>

You should see a solid block with the “Hello World” void cut out.

![visualizer-difference](resources/4/4-1.png)

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
 import pymfcad
 
 component = pymfcad.Component(
     size=(120, 40, 10), # X pixel count, Y pixel count, Z layer count
     position=(0, 0, 0),
     px_size=0.0076,
     layer_size=0.01,
 )
 
 component.add_label("default", pymfcad.Color.from_rgba((0, 255, 0, 255)))
 component.add_label("bulk", pymfcad.Color.from_name("aqua", 127))
 
 hello = pymfcad.TextExtrusion("Hello World!", height=1, font_size=15)
 hello.translate((5, 5, 9))
 component.add_void("hello", hello, label="default")
 
 bulk_cube = pymfcad.Cube((120, 40, 10))
 component.add_bulk("bulk_shape", bulk_cube, label="bulk")
 
 component.preview()
    </script>
</div>

---

## Checkpoint
Ensure that:

- You can preview the component without errors.
- You can see the text void in the visualizer.

## Next

Next: [Part 5: Modeling Introduction](5-modeling-introduction.md)

