# Installation

Prev: [Part 1: Introduction](1-introduction.md)

PyMFCAD is available on PyPI. The recommended installation method uses [uv](https://github.com/astral-sh/uv), with legacy venv/pip instructions provided for compatibility.

Choose one path below. If you already have an active environment, skip directly to the install step.

**Why use uv?**

`uv` is a fast, modern Python package manager that simplifies virtual environments and dependency management:

- Installs packages significantly faster than pip
- Automatically manages virtual environments
- Provides a simpler, more reliable workflow for modern Python projects
- Works as a drop-in replacement for pip in most cases

## Python versions

PyMFCAD supports Python 3.10–3.13.

---

## Option A — Install with uv (recommended)

1. (Optional) Create a new project directory:
```bash
mkdir my-mf-project && cd my-mf-project
```
2. Install [uv](https://github.com/astral-sh/uv) if you don't have it:
    ```bash
    pip install uv
    ```
3. Create a virtual environment and install PyMFCAD:
    ```bash
    uv venv
    uv pip install pymfcad
    ```
4. Quick verification (runs a built‑in demo):
    ```bash
    uv run python -m examples.full_test
    ```

---

## Option B — Install with venv and pip

1. Create and activate a virtual environment:
    - macOS/Linux:
      ```bash
      python3 -m venv env
      source env/bin/activate
      ```
    - Windows:
        - Command Prompt:
            ```cmd
            python -m venv env
            CALL env\Scripts\activate
            ```
        - Windows PowerShell:
            ```powershell
            python -m venv env
            .\env\Scripts\Activate.ps1
            ```
2. Install PyMFCAD from PyPI:
    ```bash
    pip install pymfcad
    ```
3. Quick verification (runs a built‑in demo):
    ```bash
    python -m examples.full_test
    ```

## Quick check

You should be able to run a demo without errors and see the visualizer open.

---

## Developing from source

If you are working from the repository, use the Makefile targets below (requires `uv`).

1. Clone or download the repository.
2. In a terminal, change into the repository root.
3. Use the targets below to install and run the project.

### Makefile targets

- `make init` — creates the virtual environment, installs Python packages, and installs JS dependencies
- `make build` — builds the docs, Vite site, and packages with uv
- `make serve` — updates docs, builds the Vite site, and serves the PyMFCAD webpage
- `make test` — runs all PyTest test cases
- `make test-coverage` — runs all PyTest test cases and outputs code coverage in htmlcov
- `make run <python file>` — runs a Python file
- `make mem-profile <python file>` — runs a Python file with heaptrack
- `make py-profile <python file>` — runs a Python file with cProfile
- `make web-install` — installs JS dependencies
- `make web-build` — builds the Vite site
- `make clean` — removes all build products

## Troubleshooting

**Issue:** `pip install uv` succeeds, but the `uv` command is not found.

**Fix:** Run `pip show uv` and add the reported install location to your PATH.

**Issue:** `pip install pymfcad` fails while building the `manifold3d` wheel.

**Fix:** Verify your Python version is supported (Python 3.10–3.13).


---

Next: [Part 3: Using the Visualizer](3-visualizer.md)
