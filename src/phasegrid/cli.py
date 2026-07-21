from __future__ import annotations

import argparse
from pathlib import Path

from .benchmark import compare_backends, write_benchmark_json
from .fit import PhaseFit
from .library import PillarLibrary
from .pipeline import PhaseGridPipeline
from .search import PhaseGridSearch
from .sweep import Sweep, parse_values
from .svg import write_layout_svg


def main() -> int:
    parser = argparse.ArgumentParser(prog="phasegrid", description="Phase fitting and sweep utilities for metalens design.")
    subparsers = parser.add_subparsers(dest="mode")

    sweep_parser = subparsers.add_parser("sweep", help="Generate parameter sweep job folders.")
    sweep_parser.add_argument("--radius", required=True, help="Radius values, e.g. 0.05:0.12:0.01 or 0.05,0.06.")
    sweep_parser.add_argument("--height", required=True, help="Height values.")
    sweep_parser.add_argument("--wavelength", required=True, help="Wavelength values.")
    sweep_parser.add_argument("--out", type=Path, default=Path("jobs"), help="Output jobs directory.")

    fit_parser = subparsers.add_parser("fit", help="Plot phase-radius fit.")
    fit_parser.add_argument("csv", type=Path, help="Sweep CSV.")
    fit_parser.add_argument("--out", type=Path, default=Path("phase_fit.svg"))
    fit_parser.add_argument("--radius-col", default="radius_um")
    fit_parser.add_argument("--phase-col", default="phase_rad")
    fit_parser.add_argument("--transmission-col", default="transmission")

    report_parser = subparsers.add_parser("library-report", help="Summarize phase/transmission coverage for a library CSV.")
    report_parser.add_argument("csv", type=Path, help="Library CSV.")
    report_parser.add_argument("--phase-cols", default=None, help="Comma-separated phase columns. Defaults to inferred phase* columns.")
    report_parser.add_argument("--transmission-cols", default=None, help="Comma-separated transmission columns. Defaults to inferred T*/transmission* columns.")
    report_parser.add_argument("--required-cols", default=None, help="Comma-separated required columns to validate.")
    report_parser.add_argument("--json", type=Path, default=None, help="Optional JSON report path.")
    report_parser.add_argument("--markdown", type=Path, default=None, help="Optional Markdown report path.")
    report_parser.add_argument("--strict", action="store_true", help="Fail if required columns are missing or phase coverage is below 2pi.")

    design_parser = subparsers.add_parser("design", help="Generate metalens layout CSV.")
    design_parser.add_argument("csv", type=Path, help="Sweep CSV.")
    design_parser.add_argument("--wavelength", type=float, required=True)
    design_parser.add_argument("--focal-length", type=float, required=True)
    design_parser.add_argument("--aperture", type=float, required=True)
    design_parser.add_argument("--pitch", type=float, required=True)
    design_parser.add_argument("--out", type=Path, default=Path("metalens_layout.csv"))
    design_parser.add_argument("--preview", type=Path, default=None, help="Optional SVG lattice preview.")
    design_parser.add_argument("--radius-col", default="radius_um")
    design_parser.add_argument("--phase-col", default="phase_rad")
    design_parser.add_argument("--transmission-col", default="transmission")

    compare_parser = subparsers.add_parser("compare", help="Compare phase/loss/geometry settings and write a leaderboard.")
    compare_parser.add_argument("csv", type=Path, help="Sweep CSV.")
    compare_parser.add_argument("--phase", default="hyperbolic", help="Comma-separated phase patterns.")
    compare_parser.add_argument("--loss", default="phase_transmission", help="Comma-separated loss names.")
    compare_parser.add_argument("--pitch", required=True, help="Pitch values, e.g. 0.25,0.3 or 0.25:0.45:0.05.")
    compare_parser.add_argument("--aperture-radius", required=True, help="Aperture radius values.")
    compare_parser.add_argument("--wavelength", required=True, help="Wavelength values.")
    compare_parser.add_argument("--focal-length", required=True, help="Focal length values.")
    compare_parser.add_argument("--out", type=Path, default=Path("phasegrid_search"))
    compare_parser.add_argument("--plot-best", action=argparse.BooleanOptionalAction, default=True)
    compare_parser.add_argument("--plot-propagation", action=argparse.BooleanOptionalAction, default=False)

    pipeline_parser = subparsers.add_parser("pipeline-demo", help="Run a full mock library-generation and design-search pipeline.")
    pipeline_parser.add_argument("--radius", default="0.05:0.16:0.01")
    pipeline_parser.add_argument("--height", default="0.6,0.7")
    pipeline_parser.add_argument("--period", default="0.35")
    pipeline_parser.add_argument("--wavelength", default="0.532")
    pipeline_parser.add_argument("--phase", default="hyperbolic,parabolic")
    pipeline_parser.add_argument("--loss", default="phase_only,phase_transmission")
    pipeline_parser.add_argument("--pitch", default="0.3,0.35")
    pipeline_parser.add_argument("--aperture-radius", default="1.0")
    pipeline_parser.add_argument("--focal-length", default="8,12")
    pipeline_parser.add_argument("--out", type=Path, default=Path("phasegrid_pipeline"))

    benchmark_parser = subparsers.add_parser("benchmark", help="Benchmark multichannel/PB selector backends.")
    benchmark_parser.add_argument("--sites", type=int, default=400)
    benchmark_parser.add_argument("--candidates", type=int, default=300)
    benchmark_parser.add_argument("--channels", type=int, default=2)
    benchmark_parser.add_argument("--rotation-steps", type=int, default=90)
    benchmark_parser.add_argument(
        "--backend",
        choices=["python", "cpp", "auto", "both"],
        default="both",
        help="Backend to benchmark. 'both' runs python, cpp, and auto.",
    )
    benchmark_parser.add_argument("--json", type=Path, default=None, help="Optional JSON output path.")

    args = parser.parse_args()
    if args.mode == "sweep":
        sweep = Sweep(radius_um=parse_values(args.radius), height_um=parse_values(args.height), wavelength_um=parse_values(args.wavelength))
        jobs = sweep.write(args.out)
        print(f"Wrote {len(jobs)} job(s) to {args.out}")
        return 0
    if args.mode == "fit":
        fit = PhaseFit.from_csv(args.csv, radius=args.radius_col, phase=args.phase_col, transmission=args.transmission_col)
        fit.to_svg(args.out)
        print(f"Wrote {args.out}")
        return 0
    if args.mode == "library-report":
        library = PillarLibrary.from_csv(args.csv)
        phase_cols = parse_optional_strings(args.phase_cols)
        transmission_cols = parse_optional_strings(args.transmission_cols)
        required_cols = parse_optional_strings(args.required_cols)
        report = (
            library.validate(phase_cols, transmission_cols, required_cols)
            if args.strict
            else library.report(phase_cols, transmission_cols, required_cols)
        )
        print(f"Candidates: {report.candidates}")
        print("Shapes: " + ", ".join(f"{key}={value}" for key, value in sorted(report.shapes.items())))
        for column, stats in report.phase.items():
            print(f"Phase {column}: span={stats.span:.6g} covers_2pi={stats.covers_2pi}")
        for column, stats in report.transmission.items():
            print(f"Transmission {column}: min={stats.minimum:.6g} max={stats.maximum:.6g} mean={stats.mean:.6g}")
        for warning in report.warnings:
            print(f"Warning: {warning}")
        if args.json:
            report.to_json(args.json)
            print(f"Wrote {args.json}")
        if args.markdown:
            report.to_markdown(args.markdown)
            print(f"Wrote {args.markdown}")
        return 0
    if args.mode == "design":
        fit = PhaseFit.from_csv(args.csv, radius=args.radius_col, phase=args.phase_col, transmission=args.transmission_col)
        layout = fit.design_lens(args.wavelength, args.focal_length, args.aperture, args.pitch)
        layout.to_csv(args.out)
        if args.preview:
            write_layout_svg(args.preview, layout)
        print(f"Wrote {len(layout.points)} layout point(s) to {args.out}")
        return 0
    if args.mode == "compare":
        search = PhaseGridSearch(
            library=args.csv,
            sweep={
                "phase": parse_strings(args.phase),
                "loss": parse_strings(args.loss),
                "pitch": parse_values(args.pitch),
                "aperture_radius": parse_values(args.aperture_radius),
                "wavelength": parse_values(args.wavelength),
                "focal_length": parse_values(args.focal_length),
            },
            fixed={
                "plot_structure": False,
                "plot_phase": False,
                "plot_propagation": args.plot_propagation,
            },
            out_dir=args.out,
            keep_plots_for_best=args.plot_best,
        )
        result = search.run()
        print(f"Wrote {len(result.runs)} run(s) to {args.out}")
        print(f"Leaderboard: {result.leaderboard_path}")
        print(f"Best: {result.best.name} score={result.best.score:.6g}")
        return 0
    if args.mode == "pipeline-demo":
        pipeline = PhaseGridPipeline(
            library_sweep={
                "radius_um": parse_values(args.radius),
                "height_um": parse_values(args.height),
                "period_um": parse_values(args.period),
                "wavelength_um": parse_values(args.wavelength),
            },
            solver="mock",
            design_sweep={
                "phase": parse_strings(args.phase),
                "loss": parse_strings(args.loss),
                "pitch": parse_values(args.pitch),
                "aperture_radius": parse_values(args.aperture_radius),
                "focal_length": parse_values(args.focal_length),
            },
            fixed={"wavelength": float(parse_values(args.wavelength)[0]), "plot_propagation": False},
            out_dir=args.out,
        )
        result = pipeline.run()
        print(f"Library: {result.library_path}")
        print(f"Leaderboard: {result.search_result.leaderboard_path}")
        print(f"Best: {result.search_result.best.name} score={result.search_result.best.score:.6g}")
        return 0
    if args.mode == "benchmark":
        backends = ["python", "cpp", "auto"] if args.backend == "both" else [args.backend]
        results = compare_backends(
            sites=args.sites,
            candidates=args.candidates,
            channels=args.channels,
            rotation_steps=args.rotation_steps,
            backends=backends,
        )
        for result in results:
            rate = result.selections_per_second
            status = result.status if result.status == "ok" else f"error: {result.error}"
            print(
                f"{result.backend}: {result.elapsed_seconds:.6f}s, "
                f"{rate:.3g} loss terms/s, status={status}"
            )
        if args.json:
            write_benchmark_json(args.json, results)
            print(f"Wrote {args.json}")
        return 0
    parser.print_help()
    return 2


def parse_strings(spec: str) -> list[str]:
    return [part.strip() for part in spec.split(",") if part.strip()]


def parse_optional_strings(spec: str | None) -> list[str] | None:
    return None if spec is None else parse_strings(spec)
