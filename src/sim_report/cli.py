from __future__ import annotations

import argparse
from pathlib import Path

from .report import build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sim-report",
        description="Generate charts, summary.md, and a parameter table from simulation results.",
    )
    parser.add_argument("results", type=Path, help="Path to the results folder to scan.")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("sim-report"),
        help="Output directory. Defaults to ./sim-report.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Report title. Defaults to the results folder name.",
    )
    parser.add_argument(
        "--max-charts",
        type=int,
        default=50,
        help="Maximum number of charts to generate. Defaults to 50.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        results_dir=args.results,
        output_dir=args.out,
        title=args.title,
        max_charts=args.max_charts,
    )
    print(f"Wrote {report.summary_path}")
    print(f"Wrote {report.parameters_path}")
    print(f"Wrote {len(report.chart_paths)} chart(s) to {report.charts_dir}")
    return 0

