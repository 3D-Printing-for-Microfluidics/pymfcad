#!/usr/bin/env python3
"""Generate custom identifier list for diff2html syntax highlighting."""
from __future__ import annotations

import builtins
import json
import keyword
import re
from pathlib import Path
from typing import Iterable

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
OUTPUT_JS = DOCS_DIR / "static" / "diff2html-identifiers.js"

SCRIPT_BLOCK_RE = re.compile(
    r"<script\s+type=\"text/plain\"\s+class=\"diff2html-source\">(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)

DEF_RE = re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\(([^)]*)\)")
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)")
ASSIGN_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=")
ANNOT_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*:")
FOR_RE = re.compile(r"^\s*for\s+([A-Za-z_]\w*)\s+in\b")
WITH_AS_RE = re.compile(r"\bas\s+([A-Za-z_]\w*)\b")
EXCEPT_AS_RE = re.compile(r"^\s*except\b.*\bas\s+([A-Za-z_]\w*)\b")

IMPORT_RE = re.compile(r"^\s*import\s+(.+)")
FROM_IMPORT_RE = re.compile(r"^\s*from\s+[\w\.]+\s+import\s+(.+)")
ATTR_CALL_RE = re.compile(r"\.([A-Za-z_]\w*)\s*\(")
CAP_IDENT_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")

EXCLUDE = set(keyword.kwlist) | set(dir(builtins)) | {"self"}


def _split_imports(segment: str) -> Iterable[str]:
    parts = [p.strip() for p in segment.split(",")]
    for part in parts:
        if not part:
            continue
        if " as " in part:
            name = part.split(" as ")[-1].strip()
        else:
            name = part.split(".")[-1].strip()
        if name:
            yield name
def _extract_params(param_text: str) -> Iterable[str]:
    if not param_text:
        return []
    params: list[str] = []
    for part in param_text.split(","):
        part = part.strip()
        if not part:
            continue
        part = part.lstrip("*")
        if ":" in part:
            part = part.split(":", 1)[0].strip()
        if "=" in part:
            part = part.split("=", 1)[0].strip()
        if part:
            params.append(part)
    return params


def _extract_names_from_line(line: str) -> Iterable[tuple[str, str]]:
    match = DEF_RE.match(line)
    if match:
        yield ("functions", match.group(1))
        for param in _extract_params(match.group(2)):
            yield ("variables", param)

    match = CLASS_RE.match(line)
    if match:
        yield ("classes", match.group(1))

    for regex in (ASSIGN_RE, ANNOT_RE, FOR_RE, EXCEPT_AS_RE):
        match = regex.match(line)
        if match:
            yield ("variables", match.group(1))

    if " as " in line:
        for match in WITH_AS_RE.finditer(line):
            yield ("variables", match.group(1))

    import_match = IMPORT_RE.match(line)
    if import_match:
        for name in _split_imports(import_match.group(1)):
            yield ("imports", name)

    from_match = FROM_IMPORT_RE.match(line)
    if from_match:
        for name in _split_imports(from_match.group(1)):
            if name and name[0].isupper():
                yield ("classes", name)
            else:
                yield ("imports", name)

    for match in ATTR_CALL_RE.finditer(line):
        yield ("functions", match.group(1))

    for match in CAP_IDENT_RE.finditer(line):
        name = match.group(1)
        if name.isupper():
            continue
        yield ("classes", name)


def _iter_diff_code_lines(text: str) -> Iterable[str]:
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("diff --git"):
            continue
        if line.startswith("index "):
            continue
        if line.startswith("--- ") or line.startswith("+++ "):
            continue
        if line.startswith("@@ "):
            continue
        if line.startswith(("+", "-", " ")):
            yield line[1:]
        else:
            yield line


def main() -> None:
    names: dict[str, set[str]] = {
        "classes": set(),
        "functions": set(),
        "variables": set(),
        "imports": set(),
    }
    for md_file in DOCS_DIR.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for block in SCRIPT_BLOCK_RE.findall(text):
            for line in _iter_diff_code_lines(block):
                for category, name in _extract_names_from_line(line):
                    if name and name not in EXCLUDE:
                        names[category].add(name)

    output = {
        "classes": sorted(names["classes"]),
        "functions": sorted(names["functions"]),
        "variables": sorted(names["variables"]),
        "imports": sorted(names["imports"]),
    }
    OUTPUT_JS.write_text(
        "window.DIFF2HTML_PY_IDENTIFIERS = "
        + json.dumps(output, indent=2)
        + ";\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
