from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


TABLE_EXTENSIONS = {".csv", ".tsv"}
METADATA_EXTENSIONS = {".json", ".yaml", ".yml"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".svg"}
LOG_EXTENSIONS = {".log", ".txt", ".out", ".err"}


@dataclass(frozen=True)
class ReportResult:
    summary_path: Path
    parameters_path: Path
    charts_dir: Path
    chart_paths: list[Path]


@dataclass(frozen=True)
class FileInventory:
    tables: list[Path]
    metadata: list[Path]
    images: list[Path]
    logs: list[Path]
    other: list[Path]


def build_report(
    results_dir: Path,
    output_dir: Path,
    title: str | None = None,
    max_charts: int = 50,
) -> ReportResult:
    results_dir = results_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not results_dir.exists():
        raise FileNotFoundError(f"Results folder does not exist: {results_dir}")
    if not results_dir.is_dir():
        raise NotADirectoryError(f"Results path is not a folder: {results_dir}")

    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    inventory = scan_results(results_dir)
    parameters = collect_parameters(results_dir, inventory.metadata)
    chart_paths = generate_charts(results_dir, charts_dir, inventory.tables, max_charts)

    output_dir.mkdir(parents=True, exist_ok=True)
    parameters_path = output_dir / "parameters.csv"
    write_parameters_csv(parameters_path, parameters)

    summary_path = output_dir / "summary.md"
    write_summary(
        summary_path=summary_path,
        title=title or f"{results_dir.name} simulation report",
        results_dir=results_dir,
        inventory=inventory,
        parameters=parameters,
        chart_paths=chart_paths,
        output_dir=output_dir,
    )

    return ReportResult(
        summary_path=summary_path,
        parameters_path=parameters_path,
        charts_dir=charts_dir,
        chart_paths=chart_paths,
    )


def scan_results(results_dir: Path) -> FileInventory:
    files = sorted(path for path in results_dir.rglob("*") if path.is_file())
    tables: list[Path] = []
    metadata: list[Path] = []
    images: list[Path] = []
    logs: list[Path] = []
    other: list[Path] = []

    for path in files:
        suffix = path.suffix.lower()
        if suffix in TABLE_EXTENSIONS:
            tables.append(path)
        elif suffix in METADATA_EXTENSIONS:
            metadata.append(path)
        elif suffix in IMAGE_EXTENSIONS:
            images.append(path)
        elif suffix in LOG_EXTENSIONS:
            logs.append(path)
        else:
            other.append(path)

    return FileInventory(tables=tables, metadata=metadata, images=images, logs=logs, other=other)


def collect_parameters(results_dir: Path, metadata_files: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in metadata_files:
        data = read_metadata(path)
        flattened = flatten_mapping(data)
        for key, value in flattened.items():
            rows.append(
                {
                    "source": path.relative_to(results_dir).as_posix(),
                    "parameter": key,
                    "value": value,
                }
            )
    return rows


def read_metadata(path: Path) -> dict[str, object]:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {"value": data}
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
        if value == "":
            child: dict[str, object] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = coerce_scalar(value)
    return data


def coerce_scalar(value: str) -> object:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return ""
    stripped = value.strip("\"'")
    try:
        if re.search(r"[.eE]", stripped):
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


def flatten_mapping(data: object, prefix: str = "") -> dict[str, str]:
    if isinstance(data, dict):
        flattened: dict[str, str] = {}
        for key, value in data.items():
            next_key = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_mapping(value, next_key))
        return flattened
    if isinstance(data, list):
        return {prefix: json.dumps(data, ensure_ascii=False)}
    return {prefix or "value": str(data)}


def generate_charts(
    results_dir: Path,
    charts_dir: Path,
    tables: Iterable[Path],
    max_charts: int,
) -> list[Path]:
    chart_paths: list[Path] = []
    for table_path in tables:
        if len(chart_paths) >= max_charts:
            break
        table = read_numeric_table(table_path)
        if not table:
            continue
        rel_stem = safe_slug(table_path.relative_to(results_dir).with_suffix("").as_posix())
        for series_name, points in table.items():
            if len(chart_paths) >= max_charts:
                break
            if len(points) < 2:
                continue
            chart_path = charts_dir / f"{rel_stem}_{safe_slug(series_name)}.svg"
            chart_path.write_text(
                render_line_chart(
                    title=f"{table_path.name}: {series_name}",
                    series_name=series_name,
                    points=points,
                ),
                encoding="utf-8",
            )
            chart_paths.append(chart_path)
    return chart_paths


def read_numeric_table(path: Path) -> dict[str, list[tuple[float, float]]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            return {}
        rows = list(reader)

    numeric_columns = {
        field: [to_float(row.get(field, "")) for row in rows]
        for field in reader.fieldnames
        if field
    }
    numeric_columns = {
        field: values
        for field, values in numeric_columns.items()
        if sum(value is not None for value in values) >= 2
    }
    if not numeric_columns:
        return {}

    x_name = choose_x_column(reader.fieldnames, numeric_columns)
    x_values = numeric_columns.get(x_name) if x_name else None
    series: dict[str, list[tuple[float, float]]] = {}
    for field, values in numeric_columns.items():
        if field == x_name:
            continue
        points: list[tuple[float, float]] = []
        for index, value in enumerate(values):
            if value is None:
                continue
            x_value = x_values[index] if x_values and x_values[index] is not None else float(index)
            points.append((float(x_value), float(value)))
        if len(points) >= 2:
            series[field] = points
    return series


def choose_x_column(fieldnames: list[str], numeric_columns: dict[str, list[float | None]]) -> str | None:
    for candidate in fieldnames:
        if candidate and candidate.lower() in {"x", "time", "step", "iteration", "iter", "epoch"}:
            if candidate in numeric_columns:
                return candidate
    return fieldnames[0] if fieldnames and fieldnames[0] in numeric_columns else None


def to_float(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def render_line_chart(title: str, series_name: str, points: list[tuple[float, float]]) -> str:
    width = 920
    height = 420
    margin_left = 72
    margin_right = 28
    margin_top = 56
    margin_bottom = 58
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = padded_domain(min(xs), max(xs))
    min_y, max_y = padded_domain(min(ys), max(ys))

    def sx(value: float) -> float:
        return margin_left + (value - min_x) / (max_x - min_x) * plot_width

    def sy(value: float) -> float:
        return margin_top + plot_height - (value - min_y) / (max_y - min_y) * plot_height

    polyline = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
    grid_lines = []
    tick_labels = []
    for index in range(5):
        fraction = index / 4
        y = margin_top + fraction * plot_height
        value = max_y - fraction * (max_y - min_y)
        grid_lines.append(f'<line x1="{margin_left}" x2="{width - margin_right}" y1="{y:.2f}" y2="{y:.2f}" />')
        tick_labels.append(f'<text x="{margin_left - 12}" y="{y + 4:.2f}" text-anchor="end">{format_tick(value)}</text>')

    escaped_title = escape_xml(title)
    escaped_series = escape_xml(series_name)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escaped_title}</title>
  <desc id="desc">Line chart for {escaped_series}</desc>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #172033; }}
    .grid line {{ stroke: #d8dee9; stroke-width: 1; }}
    .axis {{ stroke: #6b7280; stroke-width: 1.3; }}
    .series {{ fill: none; stroke: #0f766e; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }}
    .label {{ font-size: 13px; fill: #4b5563; }}
  </style>
  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="{margin_left}" y="30" font-size="20" font-weight="700">{escaped_title}</text>
  <g class="grid">
    {"".join(grid_lines)}
  </g>
  <line class="axis" x1="{margin_left}" x2="{margin_left}" y1="{margin_top}" y2="{height - margin_bottom}" />
  <line class="axis" x1="{margin_left}" x2="{width - margin_right}" y1="{height - margin_bottom}" y2="{height - margin_bottom}" />
  <g class="label">
    {"".join(tick_labels)}
    <text x="{margin_left}" y="{height - 20}">x: {format_tick(min_x)} to {format_tick(max_x)}</text>
    <text x="{width - margin_right}" y="{height - 20}" text-anchor="end">{escaped_series}</text>
  </g>
  <polyline class="series" points="{polyline}" />
</svg>
"""


def padded_domain(min_value: float, max_value: float) -> tuple[float, float]:
    if min_value == max_value:
        padding = abs(min_value) * 0.1 or 1.0
        return min_value - padding, max_value + padding
    padding = (max_value - min_value) * 0.05
    return min_value - padding, max_value + padding


def format_tick(value: float) -> str:
    return f"{value:.3g}"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return slug or "chart"


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_parameters_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "parameter", "value"])
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    summary_path: Path,
    title: str,
    results_dir: Path,
    inventory: FileInventory,
    parameters: list[dict[str, str]],
    chart_paths: list[Path],
    output_dir: Path,
) -> None:
    lines = [
        f"# {title}",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Results folder: `{results_dir}`",
        "",
        "## Inventory",
        "",
        f"- Tables: {len(inventory.tables)}",
        f"- Metadata files: {len(inventory.metadata)}",
        f"- Images: {len(inventory.images)}",
        f"- Logs: {len(inventory.logs)}",
        f"- Other files: {len(inventory.other)}",
        "",
        "## Parameters",
        "",
    ]
    if parameters:
        lines.append("| Source | Parameter | Value |")
        lines.append("| --- | --- | --- |")
        for row in parameters[:200]:
            lines.append(
                f"| {md(row['source'])} | {md(row['parameter'])} | {md(row['value'])} |"
            )
        if len(parameters) > 200:
            lines.append(f"| ... | ... | {len(parameters) - 200} more parameter rows in `parameters.csv` |")
    else:
        lines.append("No JSON/YAML parameters found.")

    lines.extend(["", "## Charts", ""])
    if chart_paths:
        for chart_path in chart_paths:
            rel = chart_path.relative_to(output_dir).as_posix()
            lines.append(f"![{chart_path.stem}]({rel})")
            lines.append("")
    else:
        lines.append("No numeric CSV/TSV series found for chart generation.")

    lines.extend(["", "## Files", ""])
    append_file_list(lines, "Tables", inventory.tables, results_dir)
    append_file_list(lines, "Metadata", inventory.metadata, results_dir)
    append_file_list(lines, "Images", inventory.images, results_dir)
    append_file_list(lines, "Logs", inventory.logs, results_dir)

    summary_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def append_file_list(lines: list[str], heading: str, paths: list[Path], results_dir: Path) -> None:
    if not paths:
        return
    lines.append(f"### {heading}")
    lines.append("")
    for path in paths[:100]:
        lines.append(f"- `{path.relative_to(results_dir).as_posix()}`")
    if len(paths) > 100:
        lines.append(f"- ... {len(paths) - 100} more")
    lines.append("")


def md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")

