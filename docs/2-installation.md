# Installation

Prev: [Part 1: Introduction](1-introduction.md)

OpenMFD is available on PyPI. The recommended installation method uses [uv](https://github.com/astral-sh/uv), but legacy venv/pip instructions are also provided.

**Why use uv?**

`uv` is a fast, modern Python package manager that simplifies virtual environments and dependency management:

- Installs packages significantly faster than pip
- Automatically manages virtual environments
- Provides a simpler, more reliable workflow for modern Python projects
- Works as a drop-in replacement for pip in most cases

## Python versions

Our dependencies currently support Python 3.10–3.13.

---

## Recommended: Install with uv

1. (Optional) Create a new project directory:
```bash
mkdir my-mfd-project && cd my-mfd-project
```
2. Install [uv](https://github.com/astral-sh/uv) if you don't have it:
    ```bash
    pip install uv
    ```
3. Create a virtual environment and install OpenMFD:
    ```bash
    uv venv
    uv pip install openmfd
    ```
4. Quick verification:
    ```bash
    uv run python -m examples.full_test
    ```

---

## Legacy: Install with venv and pip

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
2. Install OpenMFD from PyPI:
    ```bash
    pip install openmfd
    ```
3. Quick verification:
    ```bash
    python -m examples.full_test
    ```

## Developing from source

If you are working from the repository, use the Makefile targets below (requires `uv`).

1. Clone or download the repository.
2. In a terminal, change into the repository root.
3. Use the targets below to install and run the project.

### Makefile targets

- `make init` — creates the virtual environment, installs Python packages, and installs JS dependencies
- `make build` — builds the docs, Vite site, and packages with uv
- `make serve` — updates docs, builds the Vite site, and serves the OpenMFD webpage
- `make test` — runs all PyTest test cases
- `make test-coverage` —  runs all PyTest test cases. Outputs code coverage in htmlcov
- `make run <python file>` — runs a Python file
- `make mem-profile <python file>` — runs a Python file with heaptrack
- `make py-profile <python file>` — runs a Python file with cProfile
- `make web-install` — installs JS dependencies
- `make web-build` — builds the Vite site
- `make clean` — removes all build products

## Troubleshooting

**Issue:** `pip install uv` succeeds, but the `uv` command is not found.

**Fix:** Run `pip show uv` and add the reported install location to your PATH.

**Issue:** `pip install openmfd` fails while building the `manifold3d` wheel.

**Fix:** Verify your Python version is supported (Python 3.10–3.13).


---

Next: [Part 3: Using the Visualizer](3-visualizer.md)
