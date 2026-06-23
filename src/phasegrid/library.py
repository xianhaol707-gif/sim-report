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
        if self.params and key in self.params:
            return self.params[key]
        raise KeyError(key)


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

