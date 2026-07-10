from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .fit import TAU, unwrap


@dataclass(frozen=True)
class ColumnStats:
    column: str
    count: int
    minimum: float
    maximum: float
    mean: float
    span: float
    covers_2pi: bool = False


@dataclass(frozen=True)
class LibraryReport:
    candidates: int
    shapes: dict[str, int]
    phase: dict[str, ColumnStats]
    transmission: dict[str, ColumnStats]
    missing_columns: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    def to_json(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def to_markdown(self, path: str | Path) -> Path:
        path = Path(path)
        lines = [
            "# PhaseGrid Library Report",
            "",
            f"- Candidates: {self.candidates}",
            f"- Shapes: {', '.join(f'{key}={value}' for key, value in sorted(self.shapes.items())) or 'none'}",
            "",
            "## Phase Columns",
            "",
        ]
        append_stats_table(lines, self.phase, include_coverage=True)
        lines.extend(["", "## Transmission Columns", ""])
        append_stats_table(lines, self.transmission, include_coverage=False)
        if self.missing_columns:
            lines.extend(["", "## Missing Columns", ""])
            lines.extend(f"- `{column}`" for column in self.missing_columns)
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- {warning}" for warning in self.warnings)
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path


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

    def report(
        self,
        phase_columns: list[str] | None = None,
        transmission_columns: list[str] | None = None,
        required_columns: list[str] | None = None,
    ) -> LibraryReport:
        phase_columns = phase_columns or infer_columns(self.candidates, prefixes=("phase",), fallback=["phase_rad"])
        transmission_columns = transmission_columns or infer_columns(self.candidates, prefixes=("T", "transmission"), fallback=["transmission"])
        required_columns = required_columns or []
        missing_columns = [
            column
            for column in required_columns
            if not any(candidate.value(column, None) not in {None, ""} for candidate in self.candidates)
        ]
        phase_stats = {column: stats_for_column(self.candidates, column, is_phase=True) for column in phase_columns}
        transmission_stats = {column: stats_for_column(self.candidates, column, is_phase=False) for column in transmission_columns}
        phase_stats = {key: value for key, value in phase_stats.items() if value is not None}
        transmission_stats = {key: value for key, value in transmission_stats.items() if value is not None}
        warnings = build_warnings(phase_stats, transmission_stats, missing_columns)
        return LibraryReport(
            candidates=len(self.candidates),
            shapes=count_shapes(self.candidates),
            phase=phase_stats,
            transmission=transmission_stats,
            missing_columns=missing_columns,
            warnings=warnings,
        )

    def validate(
        self,
        phase_columns: list[str] | None = None,
        transmission_columns: list[str] | None = None,
        required_columns: list[str] | None = None,
        require_2pi: bool = True,
    ) -> LibraryReport:
        report = self.report(phase_columns, transmission_columns, required_columns)
        errors = list(report.missing_columns)
        if require_2pi:
            errors.extend(column for column, stats in report.phase.items() if not stats.covers_2pi)
        if errors:
            raise ValueError("Library validation failed: " + ", ".join(errors))
        return report


def phase_distance(left: float, right: float) -> float:
    return (left - right + math.pi) % TAU - math.pi


def infer_columns(candidates: list[PillarCandidate], prefixes: tuple[str, ...], fallback: list[str]) -> list[str]:
    columns = set()
    for candidate in candidates:
        for key in (candidate.params or {}):
            lowered = key.lower()
            if any(lowered == prefix.lower() or lowered.startswith(prefix.lower() + "_") for prefix in prefixes):
                columns.add(key)
    return sorted(columns or fallback)


def stats_for_column(candidates: list[PillarCandidate], column: str, is_phase: bool) -> ColumnStats | None:
    values = []
    for candidate in candidates:
        value = candidate.value(column, None)
        if value in {None, ""}:
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    sorted_values = sorted(values)
    if is_phase:
        unwrapped = unwrap(sorted_values)
        span = max(unwrapped) - min(unwrapped)
    else:
        span = max(values) - min(values)
    return ColumnStats(
        column=column,
        count=len(values),
        minimum=min(values),
        maximum=max(values),
        mean=sum(values) / len(values),
        span=span,
        covers_2pi=span >= TAU * 0.95 if is_phase else False,
    )


def count_shapes(candidates: list[PillarCandidate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.shape] = counts.get(candidate.shape, 0) + 1
    return counts


def build_warnings(
    phase_stats: dict[str, ColumnStats],
    transmission_stats: dict[str, ColumnStats],
    missing_columns: list[str],
) -> list[str]:
    warnings = []
    for column in missing_columns:
        warnings.append(f"Required column {column!r} is missing or empty.")
    for column, stats in phase_stats.items():
        if not stats.covers_2pi:
            warnings.append(f"Phase column {column!r} spans {stats.span:.3g} rad, below 0.95 * 2pi.")
    for column, stats in transmission_stats.items():
        if stats.minimum < 0.2:
            warnings.append(f"Transmission column {column!r} has low minimum {stats.minimum:.3g}.")
    return warnings


def append_stats_table(lines: list[str], stats_map: dict[str, ColumnStats], include_coverage: bool) -> None:
    if not stats_map:
        lines.append("No numeric columns found.")
        return
    if include_coverage:
        lines.append("| Column | Count | Min | Max | Mean | Span | Covers 2pi |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
        for stats in stats_map.values():
            lines.append(
                f"| {stats.column} | {stats.count} | {stats.minimum:.4g} | {stats.maximum:.4g} | {stats.mean:.4g} | {stats.span:.4g} | {stats.covers_2pi} |"
            )
    else:
        lines.append("| Column | Count | Min | Max | Mean | Span |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for stats in stats_map.values():
            lines.append(
                f"| {stats.column} | {stats.count} | {stats.minimum:.4g} | {stats.maximum:.4g} | {stats.mean:.4g} | {stats.span:.4g} |"
            )
