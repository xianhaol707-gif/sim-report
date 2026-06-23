from __future__ import annotations

import csv
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .designer import DesignResult, PhaseGridDesigner
from .library import PillarLibrary

ScoreCallable = Callable[[dict[str, float | int | str]], float]


@dataclass(frozen=True)
class SearchRun:
    index: int
    params: dict[str, Any]
    result: DesignResult
    score: float
    out_dir: Path

    @property
    def name(self) -> str:
        return f"run_{self.index:04d}"


@dataclass(frozen=True)
class SearchResult:
    runs: list[SearchRun]
    leaderboard_path: Path

    @property
    def best(self) -> SearchRun:
        if not self.runs:
            raise ValueError("SearchResult has no runs")
        return min(self.runs, key=lambda run: run.score)

    def to_csv(self, path: str | Path) -> Path:
        return write_leaderboard(Path(path), self.runs)


class PhaseGridSearch:
    def __init__(
        self,
        library: str | Path | PillarLibrary,
        sweep: dict[str, list[Any]],
        fixed: dict[str, Any] | None = None,
        score: ScoreCallable | None = None,
        out_dir: str | Path = "phasegrid_search",
        keep_plots_for_best: bool = True,
    ):
        if not sweep:
            raise ValueError("PhaseGridSearch needs at least one swept parameter")
        self.library = library if isinstance(library, PillarLibrary) else PillarLibrary.from_csv(library)
        self.sweep = {key: list(values) for key, values in sweep.items()}
        if any(not values for values in self.sweep.values()):
            raise ValueError("Sweep parameters must not be empty")
        self.fixed = dict(fixed or {})
        self.score = score or default_score
        self.out_dir = Path(out_dir)
        self.keep_plots_for_best = keep_plots_for_best

    def run(self, out_dir: str | Path | None = None) -> SearchResult:
        root = Path(out_dir) if out_dir else self.out_dir
        root.mkdir(parents=True, exist_ok=True)
        runs: list[SearchRun] = []
        combinations = list(expand_sweep(self.sweep))
        for index, params in enumerate(combinations):
            merged = dict(self.fixed)
            merged.update(params)
            run_dir = root / f"run_{index:04d}"
            plot_enabled = bool(self.keep_plots_for_best) if len(combinations) == 1 else False
            designer = PhaseGridDesigner(
                library=self.library,
                phase=merged.pop("phase", "hyperbolic"),
                loss=merged.pop("loss", "phase_transmission"),
                aperture_radius=float(merged.pop("aperture_radius", merged.pop("radius", 4.0))),
                pitch=float(merged.pop("pitch", 0.35)),
                shape=str(merged.pop("shape", "circle")),
                wavelength=pop_optional_float(merged, "wavelength"),
                focal_length=pop_optional_float(merged, "focal_length"),
                phase_params=dict(merged.pop("phase_params", {})),
                channels=merged.pop("channels", None),
                phase_mode=str(merged.pop("phase_mode", "dynamic")),
                rotation_steps=int(merged.pop("rotation_steps", 180)),
                pb_spin=int(merged.pop("pb_spin", 1)),
                loss_params=dict(merged.pop("loss_params", {})),
                out_dir=run_dir,
                plot_structure=bool(merged.pop("plot_structure", plot_enabled)),
                plot_phase=bool(merged.pop("plot_phase", plot_enabled)),
                plot_propagation=bool(merged.pop("plot_propagation", False)),
                propagation_z=pop_optional_float(merged, "propagation_z"),
                propagation_size=int(merged.pop("propagation_size", 72)),
                run_fdtd=bool(merged.pop("run_fdtd", False)),
                fdtd_runner=merged.pop("fdtd_runner", None),
                fdtd_config=dict(merged.pop("fdtd_config", {})),
                backend=str(merged.pop("backend", "auto")),
            )
            result = designer.run(run_dir)
            score = float(self.score(result.summary))
            runs.append(SearchRun(index=index, params=params, result=result, score=score, out_dir=run_dir))

        runs = sorted(runs, key=lambda run: run.score)
        if self.keep_plots_for_best and runs:
            best = runs[0]
            if "structure" not in best.result.files and "phase" not in best.result.files:
                merged = dict(self.fixed)
                merged.update(best.params)
                designer = PhaseGridDesigner(
                    library=self.library,
                    phase=merged.get("phase", "hyperbolic"),
                    loss=merged.get("loss", "phase_transmission"),
                    aperture_radius=float(merged.get("aperture_radius", merged.get("radius", 4.0))),
                    pitch=float(merged.get("pitch", 0.35)),
                    shape=str(merged.get("shape", "circle")),
                    wavelength=as_optional_float(merged.get("wavelength")),
                    focal_length=as_optional_float(merged.get("focal_length")),
                    phase_params=dict(merged.get("phase_params", {})),
                    channels=merged.get("channels", None),
                    phase_mode=str(merged.get("phase_mode", "dynamic")),
                    rotation_steps=int(merged.get("rotation_steps", 180)),
                    pb_spin=int(merged.get("pb_spin", 1)),
                    loss_params=dict(merged.get("loss_params", {})),
                    out_dir=best.out_dir,
                    plot_structure=True,
                    plot_phase=True,
                    plot_propagation=bool(merged.get("plot_propagation", False)),
                    propagation_z=as_optional_float(merged.get("propagation_z")),
                    propagation_size=int(merged.get("propagation_size", 72)),
                    backend=str(merged.get("backend", "auto")),
                )
                designer.run(best.out_dir)

        leaderboard_path = write_leaderboard(root / "leaderboard.csv", runs)
        return SearchResult(runs=runs, leaderboard_path=leaderboard_path)


def expand_sweep(sweep: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(sweep)
    return [dict(zip(keys, values)) for values in itertools.product(*(sweep[key] for key in keys))]


def default_score(summary: dict[str, float | int | str]) -> float:
    phase_error = float(summary.get("mean_abs_phase_error_rad", 0.0))
    transmission = float(summary.get("mean_transmission", 0.0))
    return phase_error - 0.2 * transmission


def write_leaderboard(path: Path, runs: list[SearchRun]) -> Path:
    fieldnames = sorted({key for run in runs for key in run.params} | {key for run in runs for key in run.result.summary})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "run", "score"] + fieldnames)
        for rank, run in enumerate(runs, start=1):
            row = [rank, run.name, run.score]
            merged = dict(run.params)
            merged.update(run.result.summary)
            row.extend(merged.get(field, "") for field in fieldnames)
            writer.writerow(row)
    return path


def pop_optional_float(values: dict[str, Any], key: str) -> float | None:
    return as_optional_float(values.pop(key, None))


def as_optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
