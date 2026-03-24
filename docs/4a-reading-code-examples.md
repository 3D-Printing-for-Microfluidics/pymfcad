# Reading Code Examples

Prev: [Part 3: Using the Visualizer](3-visualizer.md)

This short guide explains how to read the line-diff examples used throughout the documentation.

---

## How to read the examples

All examples in this guide are shown as **line diffs**:

- **Green lines** (with a `+`) are lines you need to **add/insert** at this step.
- **Red lines** (with a `-`) are lines you need to **remove**.
- **All other lines** (no `+` or `-`) stay exactly the same.

On the left side of each diff, you will see **line numbers**. These show the line numbers **before and after** the change so you can locate where the update should happen.

### Diff example

**Before** (starting file):

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 This is a example of how to read a code diff.
 You will remove this line
    </script>
</div>

**Diff** (what to change in this step):

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 This is a example of how to read a code diff.
-You will remove this line
+Add this line!!
    </script>
</div>

**After** (what your file should look like after):

<div class="diff2html-wrapper">
    <div class="diff2html"></div>
    <script type="text/plain" class="diff2html-source">
diff --git a/example_device.py b/example_device.py
index 0000000..1111111 100644
--- a/example_device.py
+++ b/example_device.py
@@ -1 +1 @@
 This is a example of how to read a code diff.
 Add this line!!
    </script>
</div>

---

Now that you know how to read the code diffs, let’s walk through a minimal example using PyMFCAD.

Next: [Part 4b: Hello World Component](4b-building_first_component.md)