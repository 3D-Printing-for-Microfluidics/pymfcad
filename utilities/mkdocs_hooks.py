from __future__ import annotations

import subprocess
from pathlib import Path

def on_pre_build(config):
    root = Path(__file__).resolve().parents[1]
    script = root / "utilities" / "generate_diff2html_identifiers.py"
    subprocess.run(["python3", str(script)], check=True)
