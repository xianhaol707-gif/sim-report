from __future__ import annotations

import math
from pathlib import Path
from typing import Any


def plot_structure(path: str | Path, sites: list[Any], aperture_radius: float) -> Path:
    path = Path(path)
    width = height = 760
    scale = (width * 0.43) / aperture_radius
    cx = cy = width / 2
    max_radius = max((site.candidate.radius for site in sites), default=1.0)
    circles = []
    for site in sites[:8000]:
        x = cx + site.x * scale
        y = cy - site.y * scale
        r = max(1.2, site.candidate.radius / max_radius * 5.0)
        circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" />')
    return write_svg(path, width, height, "structure", "".join(circles), circle_style="#0f766e")


def plot_phase(path: str | Path, sites: list[Any], aperture_radius: float) -> Path:
    path = Path(path)
    width = height = 760
    scale = (width * 0.43) / aperture_radius
    cx = cy = width / 2
    circles = []
    for site in sites[:8000]:
        x = cx + site.x * scale
        y = cy - site.y * scale
        color = phase_color(site.target_phase)
        circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="{color}" />')
    return write_svg(path, width, height, "target phase", "".join(circles), circle_style=None)


def plot_propagation(
    path: str | Path,
    sites: list[Any],
    aperture_radius: float,
    wavelength: float,
    z: float,
    size: int,
) -> Path:
    path = Path(path)
    width = height = 760
    size = max(16, min(size, 140))
    extent = aperture_radius
    k = 2.0 * math.pi / wavelength
    cells = []
    intensities = []
    for iy in range(size):
        row = []
        y = -extent + 2 * extent * iy / (size - 1)
        for ix in range(size):
            x = -extent + 2 * extent * ix / (size - 1)
            real = 0.0
            imag = 0.0
            for site in sites:
                propagation_phase = site.candidate.phase + k * ((x - site.x) ** 2 + (y - site.y) ** 2) / (2.0 * z)
                amp = math.sqrt(max(site.candidate.transmission, 0.0))
                real += amp * math.cos(propagation_phase)
                imag += amp * math.sin(propagation_phase)
            row.append(real * real + imag * imag)
        intensities.append(row)
    maximum = max(max(row) for row in intensities) or 1.0
    cell = width / size
    for iy, row in enumerate(intensities):
        for ix, value in enumerate(row):
            color = heat_color(value / maximum)
            cells.append(f'<rect x="{ix * cell:.2f}" y="{iy * cell:.2f}" width="{cell + 0.5:.2f}" height="{cell + 0.5:.2f}" fill="{color}" />')
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(cells)}</svg>\n', encoding="utf-8")
    return path


def write_svg(path: Path, width: int, height: int, title: str, body: str, circle_style: str | None) -> Path:
    style = f"circle {{ fill: {circle_style}; opacity: 0.86; }}" if circle_style else ""
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #18212f; }}
    {style}
  </style>
  <rect width="100%" height="100%" fill="#fff" />
  <text x="24" y="36" font-size="22" font-weight="700">{title}</text>
  {body}
</svg>
""",
        encoding="utf-8",
    )
    return path


def phase_color(phase: float) -> str:
    hue = (phase % (2 * math.pi)) / (2 * math.pi)
    return hsl_to_hex(hue, 0.72, 0.52)


def heat_color(value: float) -> str:
    value = max(0.0, min(1.0, value))
    hue = 0.66 - 0.66 * value
    return hsl_to_hex(hue, 0.86, 0.48)


def hsl_to_hex(h: float, s: float, l: float) -> str:
    def f(n: float) -> float:
        k = (n + h * 12) % 12
        a = s * min(l, 1 - l)
        return l - a * max(-1, min(k - 3, 9 - k, 1))

    return "#{:02x}{:02x}{:02x}".format(int(f(0) * 255), int(f(8) * 255), int(f(4) * 255))
