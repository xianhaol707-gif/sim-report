from __future__ import annotations

import argparse
from pathlib import Path

from .report import ReportOptions, build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="meep-report",
        description="Generate a Markdown report from Meep/FDTD simulation results.",
    )
    parser.add_argument("results", type=Path, help="Results folder to scan.")
    parser.add_argument("-o", "--out", type=Path, default=Path("report"), help="Output folder.")
    parser.add_argument("--title", default=None, help="Report title.")
    parser.add_argument("--max-charts", type=int, default=60, help="Maximum SVG charts to generate.")
    parser.add_argument("--max-figures", type=int, default=30, help="Maximum figures to embed in summary.md.")
    parser.add_argument(
        "--copy-figures",
        dest="copy_figures",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Copy image files into the report folder. Enabled by default.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if no recognizable simulation result files are found.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_report(
        results_dir=args.results,
        output_dir=args.out,
        options=ReportOptions(
            title=args.title,
            max_charts=args.max_charts,
            max_figures=args.max_figures,
            copy_figures=args.copy_figures,
            strict=args.strict,
        ),
    )
    print(f"Wrote {result.summary_path}")
    print(f"Wrote {result.parameters_path}")
    print(f"Wrote {result.metrics_path}")
    print(f"Wrote {result.datasets_path}")
    print(f"Copied {len(result.figure_paths)} figure(s)")
    print(f"Generated {len(result.chart_paths)} chart(s)")
    return 0

