from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from .models import Parameter


def collect_parameters(results_dir: Path, metadata_files: list[Path], script_files: list[Path]) -> list[Parameter]:
    rows: list[Parameter] = []
    for path in metadata_files:
        data = read_metadata(path)
        for name, value in flatten(data).items():
            rows.append(Parameter(relative(results_dir, path), name, value))
    for path in script_files:
        for name, value in extract_script_assignments(path).items():
            rows.append(Parameter(relative(results_dir, path), name, value))
    return rows


def read_metadata(path: Path) -> object:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return parse_simple_yaml(path.read_text(encoding="utf-8"))


def parse_simple_yaml(text: str) -> dict[str, object]:
    data: dict[str, object] = {}
    stack: list[tuple[int, dict[str, object]]] = [(-1, data)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, raw_value = line.strip().split(":", 1)
        value = raw_value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = coerce_scalar(value)
        else:
            child: dict[str, object] = {}
            parent[key] = child
            stack.append((indent, child))
    return data


def coerce_scalar(value: str) -> object:
    stripped = value.strip("\"'")
    lowered = stripped.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return ""
    try:
        if re.search(r"[.eE]", stripped):
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


def flatten(value: object, prefix: str = "") -> dict[str, str]:
    if isinstance(value, dict):
        rows: dict[str, str] = {}
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            rows.update(flatten(child, name))
        return rows
    if isinstance(value, list):
        return {prefix or "value": json.dumps(value, ensure_ascii=False)}
    return {prefix or "value": str(value)}


def extract_script_assignments(path: Path) -> dict[str, str]:
    if path.suffix.lower() == ".py":
        return extract_python_assignments(path)
    return extract_ctl_assignments(path)


def extract_python_assignments(path: Path) -> dict[str, str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return {}
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        if isinstance(value, (str, int, float, bool)):
            values[node.targets[0].id] = str(value)
    return values


def extract_ctl_assignments(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    pattern = re.compile(r"^\s*\\(define-param\s+([A-Za-z0-9_-]+)\s+([^\\s)]+)")
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.search(line)
        if match:
            values[match.group(1)] = match.group(2).strip("\"")
    return values


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()

