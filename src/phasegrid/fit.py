from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from .layout import LensLayout, LensPoint
from .svg import write_phase_svg


TAU = 2.0 * math.pi


@dataclass(frozen=True)
class PhaseSample:
    radius: float
    phase: float
    transmission: float | None = None


class PhaseFit:
    """Lookup model for radius-to-phase sweeps.

    The model keeps the implementation intentionally transparent: samples are
    sorted by radius, phase is unwrapped, and inverse lookup uses piecewise
    linear interpolation on the unwrapped phase curve.
    """

    def __init__(self, samples: list[PhaseSample]):
        if len(samples) < 2:
            raise ValueError("PhaseFit needs at least two samples")
        ordered = sorted(samples, key=lambda sample: sample.radius)
        unwrapped = unwrap([sample.phase for sample in ordered])
        base = unwrapped[0]
        normalized = [phase - base for phase in unwrapped]
        self.samples = [
            PhaseSample(sample.radius, phase, sample.transmission)
            for sample, phase in zip(ordered, normalized)
        ]

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        radius: str = "radius_um",
        phase: str = "phase_rad",
        transmission: str | None = "transmission",
    ) -> "PhaseFit":
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            samples = []
            for row in reader:
                if not row.get(radius) or not row.get(phase):
                    continue
                samples.append(
                    PhaseSample(
                        radius=float(row[radius]),
                        phase=float(row[phase]),
                        transmission=float(row[transmission]) if transmission and row.get(transmission) else None,
                    )
                )
        return cls(samples)

    @property
    def phase_span(self) -> float:
        return max(sample.phase for sample in self.samples) - min(sample.phase for sample in self.samples)

    @property
    def has_full_2pi(self) -> bool:
        return self.phase_span >= TAU * 0.95

    def radius_for_phase(self, target_phase: float) -> PhaseSample:
        target = target_phase % TAU
        phases = [sample.phase for sample in self.samples]
        minimum = min(phases)
        maximum = max(phases)
        candidates = [target + k * TAU for k in range(-3, 4)]
        usable = [candidate for candidate in candidates if minimum <= candidate <= maximum]
        query = min(usable or candidates, key=lambda candidate: distance_to_interval(candidate, minimum, maximum))
        query = min(max(query, minimum), maximum)

        for left, right in zip(self.samples, self.samples[1:]):
            low, high = sorted([left.phase, right.phase])
            if low <= query <= high:
                fraction = 0.0 if left.phase == right.phase else (query - left.phase) / (right.phase - left.phase)
                radius = left.radius + fraction * (right.radius - left.radius)
                transmission = interpolate_optional(left.transmission, right.transmission, fraction)
                phase = left.phase + fraction * (right.phase - left.phase)
                return PhaseSample(radius, phase % TAU, transmission)
        nearest = min(self.samples, key=lambda sample: abs(sample.phase - query))
        return PhaseSample(nearest.radius, nearest.phase % TAU, nearest.transmission)

    def design_lens(
        self,
        wavelength: float,
        focal_length: float,
        aperture: float,
        pitch: float,
        center: tuple[float, float] = (0.0, 0.0),
    ) -> LensLayout:
        if wavelength <= 0 or focal_length <= 0 or aperture <= 0 or pitch <= 0:
            raise ValueError("wavelength, focal_length, aperture, and pitch must be positive")
        points: list[LensPoint] = []
        radius_limit = aperture / 2.0
        half_steps = int(math.floor(radius_limit / pitch))
        cx, cy = center
        for ix in range(-half_steps, half_steps + 1):
            for iy in range(-half_steps, half_steps + 1):
                x = cx + ix * pitch
                y = cy + iy * pitch
                radial = math.hypot(x - cx, y - cy)
                if radial > radius_limit + 1e-12:
                    continue
                target = metalens_phase(radial, wavelength, focal_length)
                fitted = self.radius_for_phase(target)
                error = wrap_phase(fitted.phase - target)
                points.append(
                    LensPoint(
                        x=x,
                        y=y,
                        radius=fitted.radius,
                        target_phase=target,
                        fit_phase=fitted.phase,
                        phase_error=error,
                        transmission=fitted.transmission,
                    )
                )
        return LensLayout(points=points, wavelength=wavelength, focal_length=focal_length, aperture=aperture, pitch=pitch)

    def to_csv(self, path: str | Path) -> Path:
        path = Path(path)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["radius_um", "phase_rad", "phase_wrapped_rad", "transmission"])
            for sample in self.samples:
                writer.writerow([sample.radius, sample.phase, sample.phase % TAU, value_or_blank(sample.transmission)])
        return path

    def to_svg(self, path: str | Path) -> Path:
        return write_phase_svg(Path(path), self.samples)


def metalens_phase(radial_position: float, wavelength: float, focal_length: float) -> float:
    phase = -(TAU / wavelength) * (math.sqrt(radial_position**2 + focal_length**2) - focal_length)
    return phase % TAU


def unwrap(phases: list[float]) -> list[float]:
    if not phases:
        return []
    unwrapped = [phases[0]]
    offset = 0.0
    previous = phases[0]
    for phase in phases[1:]:
        delta = phase - previous
        if delta > math.pi:
            offset -= TAU
        elif delta < -math.pi:
            offset += TAU
        unwrapped.append(phase + offset)
        previous = phase
    return unwrapped


def wrap_phase(phase: float) -> float:
    return (phase + math.pi) % TAU - math.pi


def distance_to_interval(value: float, minimum: float, maximum: float) -> float:
    if minimum <= value <= maximum:
        return 0.0
    return min(abs(value - minimum), abs(value - maximum))


def interpolate_optional(left: float | None, right: float | None, fraction: float) -> float | None:
    if left is None or right is None:
        return left if fraction < 0.5 else right
    return left + fraction * (right - left)


def value_or_blank(value: float | None) -> str:
    return "" if value is None else str(value)

