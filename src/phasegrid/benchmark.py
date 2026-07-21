from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .backend import select_multichannel


@dataclass(frozen=True)
class BenchmarkResult:
    backend: str
    sites: int
    candidates: int
    channels: int
    rotation_steps: int
    elapsed_seconds: float
    selections: int
    status: str = "ok"
    error: str = ""

    @property
    def selections_per_second(self) -> float:
        return 0.0 if self.elapsed_seconds <= 0 else self.selections / self.elapsed_seconds

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["selections_per_second"] = self.selections_per_second
        return data


def benchmark_selector(
    sites: int = 400,
    candidates: int = 300,
    channels: int = 2,
    rotation_steps: int = 90,
    backend: str = "auto",
) -> BenchmarkResult:
    if sites <= 0 or candidates <= 0 or channels <= 0 or rotation_steps <= 0:
        raise ValueError("sites, candidates, channels, and rotation_steps must be positive")

    target_rows = make_target_rows(sites, channels)
    phase_rows = make_phase_rows(candidates, channels)
    transmission_rows = make_transmission_rows(candidates, channels)
    channel_weights = [1.0 for _ in range(channels)]
    transmission_weights = [0.2 for _ in range(channels)]
    pb_spins = [1 if index % 2 == 0 else -1 for index in range(channels)]

    started = time.perf_counter()
    try:
        select_multichannel(
            target_rows=target_rows,
            phase_rows=phase_rows,
            transmission_rows=transmission_rows,
            channel_weights=channel_weights,
            transmission_weights=transmission_weights,
            pb_spins=pb_spins,
            phase_weight=1.0,
            phase_mode="hybrid",
            rotation_steps=rotation_steps,
            pb_spin=1,
            backend=backend,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return BenchmarkResult(
            backend=backend,
            sites=sites,
            candidates=candidates,
            channels=channels,
            rotation_steps=rotation_steps,
            elapsed_seconds=elapsed,
            selections=sites * candidates * channels * rotation_steps,
            status="error",
            error=str(exc),
        )
    elapsed = time.perf_counter() - started
    return BenchmarkResult(
        backend=backend,
        sites=sites,
        candidates=candidates,
        channels=channels,
        rotation_steps=rotation_steps,
        elapsed_seconds=elapsed,
        selections=sites * candidates * channels * rotation_steps,
    )


def compare_backends(
    sites: int = 400,
    candidates: int = 300,
    channels: int = 2,
    rotation_steps: int = 90,
    backends: list[str] | None = None,
) -> list[BenchmarkResult]:
    return [
        benchmark_selector(sites, candidates, channels, rotation_steps, backend)
        for backend in (backends or ["python", "cpp", "auto"])
    ]


def write_benchmark_json(path: str | Path, results: list[BenchmarkResult]) -> Path:
    path = Path(path)
    path.write_text(json.dumps([result.to_dict() for result in results], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def make_target_rows(sites: int, channels: int) -> list[list[float]]:
    return [
        [wrap(0.017 * site + 0.31 * channel + 0.2 * math.sin(site * 0.13 + channel)) for channel in range(channels)]
        for site in range(sites)
    ]


def make_phase_rows(candidates: int, channels: int) -> list[list[float]]:
    return [
        [wrap(0.053 * candidate + 0.47 * channel + 0.1 * math.cos(candidate * 0.07 + channel)) for channel in range(channels)]
        for candidate in range(candidates)
    ]


def make_transmission_rows(candidates: int, channels: int) -> list[list[float]]:
    rows = []
    for candidate in range(candidates):
        row = []
        for channel in range(channels):
            value = 0.58 + 0.34 * (0.5 + 0.5 * math.sin(candidate * 0.11 + channel * 0.7))
            row.append(max(0.05, min(0.98, value)))
        rows.append(row)
    return rows


def wrap(value: float) -> float:
    return value % (2.0 * math.pi)

