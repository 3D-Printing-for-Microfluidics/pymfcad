# Installation

Prev: [Part 1: Introduction](1-introduction.md)

OpenMFD is available on PyPI. The recommended installation method uses [uv](https://github.com/astral-sh/uv), but legacy venv/pip instructions are also provided.

**Why use uv?**

`uv` is a fast, modern Python package manager that makes working with virtual environments and dependencies much easier:

- Installs packages significantly faster than pip
- Automatically manages virtual environments for you
- Provides a simpler, more reliable workflow for modern Python projects
- Works as a drop-in replacement for pip in most cases

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

If you are developing from source (this repo):
```bash
uv pip install -e .
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
            ```
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

If you are developing from source (this repo):
```bash
pip install -e .
```

---

Next: [Part 3: Using the Visualizer](3-visualizer.md)
