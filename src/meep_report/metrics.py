from __future__ import annotations

import csv
import math
from pathlib import Path

from .models import MetricPoint


X_COLUMN_NAMES = {"x", "time", "step", "iteration", "iter", "epoch", "freq", "frequency", "wavelength"}


def collect_metrics(results_dir: Path, table_files: list[Path]) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for path in table_files:
        series = read_numeric_series(path)
        source = path.relative_to(results_dir).as_posix()
        for name, points in series.items():
            rows.extend(MetricPoint(source, name, x, y) for x, y in points)
    return rows


def read_numeric_series(path: Path) -> dict[str, list[tuple[float, float]]]:
    delimiter = infer_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        if delimiter is None:
            return read_whitespace_table(handle.read())
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            return {}
        rows = list(reader)
    numeric = {
        field: [to_float(row.get(field)) for row in rows]
        for field in reader.fieldnames
        if field
    }
    numeric = {field: values for field, values in numeric.items() if count_numbers(values) >= 2}
    if not numeric:
        return {}
    x_name = choose_x_column(list(reader.fieldnames), numeric)
    x_values = numeric.get(x_name) if x_name else None
    return build_series(numeric, x_name, x_values)


def infer_delimiter(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return ","
    if suffix == ".tsv":
        return "\t"
    return None


def read_whitespace_table(text: str) -> dict[str, list[tuple[float, float]]]:
    rows: list[list[float]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = [to_float(part) for part in stripped.split()]
        if all(value is not None for value in values) and len(values) >= 2:
            rows.append([float(value) for value in values if value is not None])
    if len(rows) < 2:
        return {}
    width = min(len(row) for row in rows)
    columns = {f"col_{index}": [row[index] for row in rows] for index in range(width)}
    return build_series(columns, "col_0", columns["col_0"])


def build_series(
    numeric: dict[str, list[float | None]],
    x_name: str | None,
    x_values: list[float | None] | None,
) -> dict[str, list[tuple[float, float]]]:
    series: dict[str, list[tuple[float, float]]] = {}
    for name, values in numeric.items():
        if name == x_name:
            continue
        points: list[tuple[float, float]] = []
        for index, value in enumerate(values):
            if value is None:
                continue
            x = x_values[index] if x_values and x_values[index] is not None else float(index)
            points.append((float(x), float(value)))
        if len(points) >= 2:
            series[name] = points
    return series


def choose_x_column(fieldnames: list[str], numeric: dict[str, list[float | None]]) -> str | None:
    for field in fieldnames:
        if field and field.lower() in X_COLUMN_NAMES and field in numeric:
            return field
    return fieldnames[0] if fieldnames and fieldnames[0] in numeric else None


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value.strip())
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def count_numbers(values: list[float | None]) -> int:
    return sum(value is not None for value in values)

