from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .search import PhaseGridSearch, SearchResult
from .solvers import SolverRunner, resolve_solver
from .sweep import Job, Sweep


@dataclass(frozen=True)
class PipelineResult:
    library_path: Path
    search_result: SearchResult
    summary_path: Path
    files: dict[str, Path]


class PhaseGridPipeline:
    def __init__(
        self,
        library_sweep: dict[str, list[Any]],
        design_sweep: dict[str, list[Any]],
        fixed: dict[str, Any] | None = None,
        solver: str | SolverRunner | Callable[[Job, Path, dict[str, Any]], dict[str, Any]] = "mock",
        solver_runner: SolverRunner | Callable[[Job, Path, dict[str, Any]], dict[str, Any]] | None = None,
        solver_config: dict[str, Any] | None = None,
        score: Callable[[dict[str, float | int | str]], float] | None = None,
        validate_best: int = 0,
        validation_runner: Callable[[Any, Path, dict[str, Any]], dict[str, Any] | None] | None = None,
        validation_config: dict[str, Any] | None = None,
        out_dir: str | Path = "phasegrid_pipeline",
    ):
        self.library_sweep = {key: list(values) for key, values in library_sweep.items()}
        self.design_sweep = {key: list(values) for key, values in design_sweep.items()}
        self.fixed = dict(fixed or {})
        if solver_runner is not None:
            self.solver = resolve_solver(solver_runner)
        else:
            self.solver = resolve_solver(solver)
        self.solver_config = dict(solver_config or {})
        self.score = score
        self.validate_best = validate_best
        self.validation_runner = validation_runner
        self.validation_config = dict(validation_config or {})
        self.out_dir = Path(out_dir)

    def run(self, out_dir: str | Path | None = None) -> PipelineResult:
        root = Path(out_dir) if out_dir else self.out_dir
        root.mkdir(parents=True, exist_ok=True)
        jobs_dir = root / "library_jobs"
        results_dir = root / "library_results"
        search_dir = root / "search"
        validation_dir = root / "validation"

        jobs = Sweep(**self.library_sweep).write(jobs_dir)
        library_path = self._run_library_jobs(jobs, results_dir)
        search = PhaseGridSearch(
            library=library_path,
            sweep=self.design_sweep,
            fixed=self.fixed,
            score=self.score,
            out_dir=search_dir,
            keep_plots_for_best=True,
        )
        search_result = search.run()
        files = {
            "library_manifest": jobs_dir / "manifest.csv",
            "library": library_path,
            "leaderboard": search_result.leaderboard_path,
        }
        if self.validate_best:
            if self.validation_runner is None:
                raise ValueError("validate_best > 0 requires validation_runner")
            files.update(self._validate_best(search_result, validation_dir))
        summary_path = self._write_summary(root / "pipeline_summary.json", search_result, library_path, files)
        files["summary"] = summary_path
        return PipelineResult(library_path=library_path, search_result=search_result, summary_path=summary_path, files=files)

    def _run_library_jobs(self, jobs: list[Job], results_dir: Path) -> Path:
        results_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, Any]] = []
        for job in jobs:
            job_dir = results_dir / job.name
            job_dir.mkdir(parents=True, exist_ok=True)
            output = self.solver.run(job, job_dir, dict(self.solver_config))
            rows.append(normalize_library_row(job.params, output))
            (job_dir / "result.json").write_text(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        library_path = results_dir / "library.csv"
        write_rows(library_path, rows)
        return library_path

    def _validate_best(self, search_result: SearchResult, validation_dir: Path) -> dict[str, Path]:
        validation_dir.mkdir(parents=True, exist_ok=True)
        files: dict[str, Path] = {}
        for rank, run in enumerate(search_result.runs[: self.validate_best], start=1):
            out_dir = validation_dir / f"best_{rank:04d}_{run.name}"
            out_dir.mkdir(parents=True, exist_ok=True)
            output = self.validation_runner(run.result, out_dir, dict(self.validation_config)) or {}
            path = out_dir / "summary.json"
            path.write_text(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
            files[f"validation_{rank}"] = path
        return files

    def _write_summary(self, path: Path, search_result: SearchResult, library_path: Path, files: dict[str, Path]) -> Path:
        summary = {
            "library_path": str(library_path),
            "design_runs": len(search_result.runs),
            "best_run": search_result.best.name if search_result.runs else "",
            "best_score": search_result.best.score if search_result.runs else None,
            "files": {key: str(value) for key, value in files.items()},
        }
        path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path


def normalize_library_row(params: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    row = dict(params)
    row.update(output)
    if "radius_um" not in row and "radius" in row:
        row["radius_um"] = row["radius"]
    if "phase_rad" not in row and "phase" in row:
        row["phase_rad"] = row["phase"]
    if "transmission" not in row and "T" in row:
        row["transmission"] = row["T"]
    required = {"radius_um", "phase_rad", "transmission"}
    missing = sorted(key for key in required if key not in row or row[key] == "")
    if missing:
        raise ValueError(f"solver output missing required library columns: {', '.join(missing)}")
    return row


def write_rows(path: Path, rows: list[dict[str, Any]]) -> Path:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 0:
        raise ValueError("count must be positive")
    if count == 1:
        return [float(start)]
    step = (stop - start) / (count - 1)
    return [start + step * index for index in range(count)]


def arange(start: float, stop: float, step: float) -> list[float]:
    if step == 0:
        raise ValueError("step cannot be zero")
    values = []
    value = start
    compare = (lambda x: x <= stop + 1e-12) if step > 0 else (lambda x: x >= stop - 1e-12)
    while compare(value):
        values.append(round(value, 12))
        value += step
    return values
