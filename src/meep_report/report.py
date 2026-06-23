from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .charts import write_metric_charts
from .hdf5 import summarize_hdf5
from .logs import scan_logs
from .metrics import collect_metrics
from .models import DatasetSummary, Inventory, LogFinding, MetricPoint, Parameter
from .parameters import collect_parameters
from .scanner import scan_results


@dataclass(frozen=True)
class ReportOptions:
    title: str | None = None
    max_charts: int = 60
    max_figures: int = 30
    copy_figures: bool = True
    strict: bool = False


@dataclass(frozen=True)
class ReportResult:
    summary_path: Path
    parameters_path: Path
    metrics_path: Path
    datasets_path: Path
    chart_paths: list[Path]
    figure_paths: list[Path]


def build_report(results_dir: Path, output_dir: Path, options: ReportOptions | None = None) -> ReportResult:
    options = options or ReportOptions()
    results_dir = results_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not results_dir.exists():
        raise FileNotFoundError(f"Results folder does not exist: {results_dir}")
    if not results_dir.is_dir():
        raise NotADirectoryError(f"Results path is not a folder: {results_dir}")

    inventory = scan_results(results_dir)
    if options.strict and not has_recognized_files(inventory):
        raise ValueError(f"No recognizable Meep/FDTD result files found in {results_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = output_dir / "charts"
    figures_dir = output_dir / "figures"

    parameters = collect_parameters(results_dir, inventory.parameters, inventory.scripts)
    metrics = collect_metrics(results_dir, inventory.tables)
    datasets = summarize_hdf5(results_dir, inventory.hdf5)
    logs = scan_logs(results_dir, inventory.logs)
    chart_paths = write_metric_charts(metrics, charts_dir, options.max_charts)
    figure_paths = copy_figures(results_dir, inventory.figures, figures_dir, options.copy_figures)

    parameters_path = output_dir / "parameters.csv"
    metrics_path = output_dir / "metrics.csv"
    datasets_path = output_dir / "datasets.csv"
    summary_path = output_dir / "summary.md"

    write_parameters(parameters_path, parameters)
    write_metrics(metrics_path, metrics)
    write_datasets(datasets_path, datasets)
    write_summary(
        summary_path=summary_path,
        output_dir=output_dir,
        results_dir=results_dir,
        title=options.title or f"{results_dir.name} Meep/FDTD report",
        inventory=inventory,
        parameters=parameters,
        metrics=metrics,
        datasets=datasets,
        logs=logs,
        chart_paths=chart_paths,
        figure_paths=figure_paths[: options.max_figures],
    )

    return ReportResult(summary_path, parameters_path, metrics_path, datasets_path, chart_paths, figure_paths)


def has_recognized_files(inventory: Inventory) -> bool:
    return any(
        [
            inventory.parameters,
            inventory.tables,
            inventory.figures,
            inventory.hdf5,
            inventory.logs,
            inventory.scripts,
        ]
    )


def copy_figures(results_dir: Path, figures: list[Path], figures_dir: Path, enabled: bool) -> list[Path]:
    if not enabled:
        return figures
    figures_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for path in figures:
        relative = path.relative_to(results_dir)
        destination = figures_dir / sanitize_path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied.append(destination)
    return copied


def sanitize_path(path: Path) -> Path:
    parts = [part.replace(" ", "_") for part in path.parts]
    return Path(*parts)


def write_parameters(path: Path, rows: list[Parameter]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "parameter", "value"])
        writer.writerows((row.source, row.name, row.value) for row in rows)


def write_metrics(path: Path, rows: list[MetricPoint]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "series", "x", "y"])
        writer.writerows((row.source, row.series, row.x, row.y) for row in rows)


def write_datasets(path: Path, rows: list[DatasetSummary]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "dataset", "shape", "dtype", "min", "max", "mean"])
        writer.writerows((row.source, row.dataset, row.shape, row.dtype, row.minimum, row.maximum, row.mean) for row in rows)


def write_summary(
    summary_path: Path,
    output_dir: Path,
    results_dir: Path,
    title: str,
    inventory: Inventory,
    parameters: list[Parameter],
    metrics: list[MetricPoint],
    datasets: list[DatasetSummary],
    logs: list[LogFinding],
    chart_paths: list[Path],
    figure_paths: list[Path],
) -> None:
    lines = [
        f"# {title}",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"Results folder: `{results_dir}`",
        "",
        "## Run Inventory",
        "",
        f"- Parameter files: {len(inventory.parameters)}",
        f"- Script files: {len(inventory.scripts)}",
        f"- Metric tables: {len(inventory.tables)}",
        f"- Figure files: {len(inventory.figures)}",
        f"- HDF5 files: {len(inventory.hdf5)}",
        f"- Logs: {len(inventory.logs)}",
        f"- Other files: {len(inventory.other)}",
        "",
        "## Highlights",
        "",
        f"- Extracted {len(parameters)} parameter row(s).",
        f"- Extracted {len(metrics)} metric point(s).",
        f"- Summarized {len(datasets)} HDF5 dataset row(s).",
        f"- Found {len(logs)} notable log line(s).",
        "",
        "## Parameters",
        "",
    ]
    append_parameter_table(lines, parameters)
    lines.extend(["", "## Metric Charts", ""])
    append_media(lines, output_dir, chart_paths, "No numeric metric charts were generated.")
    lines.extend(["", "## Figures", ""])
    append_media(lines, output_dir, figure_paths, "No figures were found.")
    lines.extend(["", "## HDF5 Datasets", ""])
    append_dataset_table(lines, datasets)
    lines.extend(["", "## Log Findings", ""])
    append_log_table(lines, logs)
    lines.extend(["", "## Source Files", ""])
    append_file_list(lines, "Parameter files", inventory.parameters, results_dir)
    append_file_list(lines, "Scripts", inventory.scripts, results_dir)
    append_file_list(lines, "Metric tables", inventory.tables, results_dir)
    append_file_list(lines, "HDF5 files", inventory.hdf5, results_dir)
    append_file_list(lines, "Logs", inventory.logs, results_dir)

    summary_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def append_parameter_table(lines: list[str], rows: list[Parameter]) -> None:
    if not rows:
        lines.append("No parameters were extracted.")
        return
    lines.extend(["| Source | Parameter | Value |", "| --- | --- | --- |"])
    for row in rows[:120]:
        lines.append(f"| {md(row.source)} | {md(row.name)} | {md(row.value)} |")
    if len(rows) > 120:
        lines.append(f"| ... | ... | {len(rows) - 120} more rows in `parameters.csv` |")


def append_dataset_table(lines: list[str], rows: list[DatasetSummary]) -> None:
    if not rows:
        lines.append("No HDF5 datasets were found.")
        return
    lines.extend(["| Source | Dataset | Shape | Dtype | Min | Max | Mean |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for row in rows[:120]:
        lines.append(
            f"| {md(row.source)} | {md(row.dataset)} | {md(row.shape)} | {md(row.dtype)} | {md(row.minimum)} | {md(row.maximum)} | {md(row.mean)} |"
        )
    if len(rows) > 120:
        lines.append(f"| ... | ... | ... | ... | ... | ... | {len(rows) - 120} more rows in `datasets.csv` |")


def append_log_table(lines: list[str], rows: list[LogFinding]) -> None:
    if not rows:
        lines.append("No warning/error/completion lines were detected in logs.")
        return
    lines.extend(["| Source | Level | Line | Message |", "| --- | --- | ---: | --- |"])
    for row in rows[:80]:
        lines.append(f"| {md(row.source)} | {md(row.level)} | {row.line_number} | {md(row.message)} |")
    if len(rows) > 80:
        lines.append(f"| ... | ... | ... | {len(rows) - 80} more rows omitted |")


def append_media(lines: list[str], output_dir: Path, paths: list[Path], empty_message: str) -> None:
    if not paths:
        lines.append(empty_message)
        return
    for path in paths:
        rel = path.relative_to(output_dir).as_posix() if path.is_relative_to(output_dir) else path.as_posix()
        lines.append(f"![{md(path.stem)}]({rel})")
        lines.append("")


def append_file_list(lines: list[str], heading: str, paths: list[Path], root: Path) -> None:
    if not paths:
        return
    lines.extend([f"### {heading}", ""])
    for path in paths[:100]:
        lines.append(f"- `{path.relative_to(root).as_posix()}`")
    if len(paths) > 100:
        lines.append(f"- ... {len(paths) - 100} more")
    lines.append("")


def md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")

