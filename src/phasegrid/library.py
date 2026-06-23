from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fit import TAU, unwrap


@dataclass(frozen=True)
class PillarCandidate:
    radius: float
    phase: float
    transmission: float = 1.0
    height: float | None = None
    shape: str = "circle"
    width: float | None = None
    length: float | None = None
    rotation: float | None = None
    params: dict[str, Any] | None = None

    def __getitem__(self, key: str) -> Any:
        if key in {"radius", "radius_um", "r_um"}:
            return self.radius
        if key in {"phase", "phase_rad"}:
            return self.phase
        if key in {"transmission", "T"}:
            return self.transmission
        if key in {"height", "height_um", "h_um"}:
            return self.height
        if key in {"shape", "meta_atom", "geometry"}:
            return self.shape
        if key in {"width", "width_um", "w_um"}:
            return self.width
        if key in {"length", "length_um", "l_um"}:
            return self.length
        if key in {"rotation", "rotation_rad"}:
            return self.rotation
        if key == "rotation_deg":
            return None if self.rotation is None else math.degrees(self.rotation)
        if self.params and key in self.params:
            return self.params[key]
        raise KeyError(key)

    def value(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def phase_for(self, column: str = "phase_rad") -> float:
        value = self.value(column, None)
        return self.phase if value is None or value == "" else float(value)

    def transmission_for(self, column: str = "transmission") -> float:
        value = self.value(column, None)
        return self.transmission if value is None or value == "" else float(value)

    def with_rotation(self, rotation: float | None) -> "PillarCandidate":
        return PillarCandidate(
            radius=self.radius,
            phase=self.phase,
            transmission=self.transmission,
            height=self.height,
            shape=self.shape,
            width=self.width,
            length=self.length,
            rotation=rotation,
            params=self.params,
        )


class PillarLibrary:
    def __init__(self, candidates: list[PillarCandidate]):
        if not candidates:
            raise ValueError("PillarLibrary needs at least one candidate")
        ordered = sorted(candidates, key=lambda candidate: candidate.radius)
        phases = unwrap([candidate.phase for candidate in ordered])
        base = phases[0]
        self.candidates = [
            PillarCandidate(
                radius=candidate.radius,
                phase=(phase - base) % TAU,
                transmission=candidate.transmission,
                height=candidate.height,
                shape=candidate.shape,
                width=candidate.width,
                length=candidate.length,
                rotation=candidate.rotation,
                params=candidate.params or {},
            )
            for candidate, phase in zip(ordered, phases)
        ]

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        radius: str = "radius_um",
        phase: str = "phase_rad",
        transmission: str = "transmission",
        height: str | None = "height_um",
        shape: str | None = "shape",
        width: str | None = "width_um",
        length: str | None = "length_um",
    ) -> "PillarLibrary":
        candidates: list[PillarCandidate] = []
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if not row.get(radius) or not row.get(phase):
                    continue
                extras = dict(row)
                candidates.append(
                    PillarCandidate(
                        radius=float(row[radius]),
                        phase=float(row[phase]),
                        transmission=float(row[transmission]) if row.get(transmission) else 1.0,
                        height=float(row[height]) if height and row.get(height) else None,
                        shape=row.get(shape, "circle") if shape else "circle",
                        width=float(row[width]) if width and row.get(width) else None,
                        length=float(row[length]) if length and row.get(length) else None,
                        params=extras,
                    )
                )
        return cls(candidates)

    @property
    def radii(self) -> list[float]:
        return [candidate.radius for candidate in self.candidates]

    @property
    def phases(self) -> list[float]:
        return [candidate.phase for candidate in self.candidates]

    @property
    def transmissions(self) -> list[float]:
        return [candidate.transmission for candidate in self.candidates]


def phase_distance(left: float, right: float) -> float:
    return (left - right + math.pi) % TAU - math.pi
