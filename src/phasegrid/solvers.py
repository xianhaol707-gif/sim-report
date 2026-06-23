from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol


class SolverRunner(Protocol):
    def run(self, job: Any, out_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class CustomSolver:
    runner: Callable[[Any, Path, dict[str, Any]], dict[str, Any]]

    def run(self, job: Any, out_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
        return self.runner(job, out_dir, config)


@dataclass(frozen=True)
class MockSolver:
    """Deterministic local solver for examples and pipeline testing.

    It is not a physical RCWA/FDTD solver. It generates smooth phase and
    transmission values from sweep parameters so the full pipeline can run
    without external dependencies.
    """

    phase_scale: float = 54.0
    height_scale: float = 1.7
    transmission_center: float = 0.105
    transmission_width: float = 0.055

    def run(self, job: Any, out_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        radius = float(job.params.get("radius_um", job.params.get("radius", 0.1)))
        height = float(job.params.get("height_um", job.params.get("height", 0.6)))
        wavelength = float(job.params.get("wavelength_um", job.params.get("wavelength", config.get("wavelength", 0.532))))
        phase = (self.phase_scale * radius + self.height_scale * height + 0.2 / wavelength) % (2 * math.pi)
        distance = (radius - self.transmission_center) / self.transmission_width
        transmission = max(0.05, min(0.98, 0.9 * math.exp(-0.5 * distance * distance) + 0.08))
        return {
            "phase_rad": phase,
            "transmission": transmission,
            "radius_um": radius,
            "height_um": height,
            "wavelength_um": wavelength,
            "solver": "mock",
        }


def resolve_solver(solver: str | SolverRunner | Callable[[Any, Path, dict[str, Any]], dict[str, Any]]) -> SolverRunner:
    if isinstance(solver, str):
        name = solver.lower()
        if name == "mock":
            return MockSolver()
        if name in {"custom", "fdtd", "rcwa"}:
            raise ValueError(f"solver={solver!r} requires solver_runner")
        raise ValueError(f"Unknown solver: {solver}")
    if callable(solver) and not hasattr(solver, "run"):
        return CustomSolver(solver)
    return solver

