from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

from .models import MetricPoint


def write_metric_charts(metrics: list[MetricPoint], charts_dir: Path, max_charts: int) -> list[Path]:
    charts_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for point in metrics:
        grouped[(point.source, point.series)].append((point.x, point.y))

    paths: list[Path] = []
    for (source, series), points in sorted(grouped.items()):
        if len(paths) >= max_charts:
            break
        if len(points) < 2:
            continue
        name = f"{slug(Path(source).stem)}_{slug(series)}.svg"
        path = charts_dir / name
        path.write_text(render_line_chart(f"{source}: {series}", points), encoding="utf-8")
        paths.append(path)
    return paths


def render_line_chart(title: str, points: list[tuple[float, float]]) -> str:
    width, height = 960, 420
    left, right, top, bottom = 74, 28, 56, 58
    plot_width, plot_height = width - left - right, height - top - bottom
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = domain(xs)
    min_y, max_y = domain(ys)

    def sx(value: float) -> float:
        return left + (value - min_x) / (max_x - min_x) * plot_width

    def sy(value: float) -> float:
        return top + plot_height - (value - min_y) / (max_y - min_y) * plot_height

    polyline = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in points)
    y_grid = []
    y_labels = []
    for index in range(5):
        fraction = index / 4
        y = top + fraction * plot_height
        value = max_y - fraction * (max_y - min_y)
        y_grid.append(f'<line x1="{left}" x2="{width - right}" y1="{y:.2f}" y2="{y:.2f}" />')
        y_labels.append(f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end">{tick(value)}</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #18212f; }}
    .grid line {{ stroke: #d8dee9; stroke-width: 1; }}
    .axis {{ stroke: #667085; stroke-width: 1.3; }}
    .series {{ fill: none; stroke: #0f766e; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }}
    .label {{ font-size: 13px; fill: #475467; }}
  </style>
  <rect width="100%" height="100%" fill="#ffffff" />
  <text x="{left}" y="31" font-size="20" font-weight="700">{xml(title)}</text>
  <g class="grid">{"".join(y_grid)}</g>
  <line class="axis" x1="{left}" x2="{left}" y1="{top}" y2="{height - bottom}" />
  <line class="axis" x1="{left}" x2="{width - right}" y1="{height - bottom}" y2="{height - bottom}" />
  <g class="label">
    {"".join(y_labels)}
    <text x="{left}" y="{height - 22}">x: {tick(min_x)} to {tick(max_x)}</text>
  </g>
  <polyline class="series" points="{polyline}" />
</svg>
"""


def domain(values: list[float]) -> tuple[float, float]:
    minimum, maximum = min(values), max(values)
    if not math.isfinite(minimum) or not math.isfinite(maximum):
        return 0.0, 1.0
    if minimum == maximum:
        pad = abs(minimum) * 0.1 or 1.0
        return minimum - pad, maximum + pad
    pad = (maximum - minimum) * 0.05
    return minimum - pad, maximum + pad


def tick(value: float) -> str:
    return f"{value:.4g}"


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "metric"


def xml(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

