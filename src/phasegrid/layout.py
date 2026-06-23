from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LensPoint:
    x: float
    y: float
    radius: float
    target_phase: float
    fit_phase: float
    phase_error: float
    transmission: float | None = None


@dataclass(frozen=True)
class LensLayout:
    points: list[LensPoint]
    wavelength: float
    focal_length: float
    aperture: float
    pitch: float

    def to_csv(self, path: str | Path) -> Path:
        path = Path(path)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["x_um", "y_um", "r_um", "target_phase_rad", "fit_phase_rad", "phase_error_rad", "transmission"])
            for point in self.points:
                writer.writerow(
                    [
                        point.x,
                        point.y,
                        point.radius,
                        point.target_phase,
                        point.fit_phase,
                        point.phase_error,
                        "" if point.transmission is None else point.transmission,
                    ]
                )
        return path

    def summary(self) -> dict[str, float | int]:
        mean_error = sum(abs(point.phase_error) for point in self.points) / len(self.points) if self.points else 0.0
        return {
            "points": len(self.points),
            "wavelength_um": self.wavelength,
            "focal_length_um": self.focal_length,
            "aperture_um": self.aperture,
            "pitch_um": self.pitch,
            "mean_abs_phase_error_rad": mean_error,
        }

