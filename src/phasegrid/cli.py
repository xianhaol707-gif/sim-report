from __future__ import annotations

import argparse
from pathlib import Path

from .fit import PhaseFit
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
    parser.print_help()
    return 2


def parse_strings(spec: str) -> list[str]:
    return [part.strip() for part in spec.split(",") if part.strip()]
