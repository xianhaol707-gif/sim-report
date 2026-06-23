from __future__ import annotations

from pathlib import Path

from .layout import LensLayout


def write_phase_svg(path: Path, samples: object) -> Path:
    data = [(sample.radius, sample.phase) for sample in samples]
    return write_xy_svg(path, "phase-radius fit", "radius", "phase", data)


def write_layout_svg(path: str | Path, layout: LensLayout) -> Path:
    data = [(point.x, point.y) for point in layout.points]
    return write_xy_svg(Path(path), "lens lattice", "x", "y", data, connect=False)


def write_xy_svg(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    data: list[tuple[float, float]],
    connect: bool = True,
) -> Path:
    width, height = 860, 420
    left, right, top, bottom = 70, 24, 50, 58
    xs = [x for x, _ in data] or [0.0, 1.0]
    ys = [y for _, y in data] or [0.0, 1.0]
    min_x, max_x = padded(min(xs), max(xs))
    min_y, max_y = padded(min(ys), max(ys))

    def sx(value: float) -> float:
        return left + (value - min_x) / (max_x - min_x) * (width - left - right)

    def sy(value: float) -> float:
        return top + (max_y - value) / (max_y - min_y) * (height - top - bottom)

    points = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in data)
    circles = "\n".join(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="3" />' for x, y in data[:4000])
    line = f'<polyline class="line" points="{points}" />' if connect and len(data) >= 2 else ""
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #18212f; }}
    .axis {{ stroke: #667085; stroke-width: 1.2; }}
    .line {{ fill: none; stroke: #0f766e; stroke-width: 3; }}
    circle {{ fill: #2563eb; opacity: 0.82; }}
  </style>
  <rect width="100%" height="100%" fill="#fff" />
  <text x="{left}" y="30" font-size="20" font-weight="700">{escape(title)}</text>
  <line class="axis" x1="{left}" x2="{left}" y1="{top}" y2="{height - bottom}" />
  <line class="axis" x1="{left}" x2="{width - right}" y1="{height - bottom}" y2="{height - bottom}" />
  <text x="{left}" y="{height - 20}" font-size="13">{escape(x_label)}: {min_x:.4g} to {max_x:.4g}</text>
  <text x="{width - right}" y="{height - 20}" text-anchor="end" font-size="13">{escape(y_label)}: {min_y:.4g} to {max_y:.4g}</text>
  {line}
  {circles}
</svg>
""",
        encoding="utf-8",
    )
    return path


def padded(minimum: float, maximum: float) -> tuple[float, float]:
    if minimum == maximum:
        pad = abs(minimum) * 0.1 or 1.0
        return minimum - pad, maximum + pad
    pad = (maximum - minimum) * 0.05
    return minimum - pad, maximum + pad


def escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

