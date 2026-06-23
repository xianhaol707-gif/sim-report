# phasegrid

Fast phase-radius fitting plus parameter sweep utilities for metalens and metasurface design.

`phasegrid` is a small Python package for a common workflow:

1. Generate parameter sweep jobs for nanopillar/unit-cell simulations.
2. Read the completed sweep table.
3. Fit the radius-to-phase lookup curve.
4. Convert a target metalens phase profile into a fabrication/simulation layout.

It uses only the Python standard library, so it works on laptops, clusters, and minimal remote nodes.

## Install

```bash
python -m pip install --no-build-isolation .
```

For local development:

```bash
PYTHONPATH=src python -m phasegrid design examples/sweep.csv --out /tmp/layout.csv \
  --wavelength 0.532 --focal-length 12 --aperture 8 --pitch 0.35
```

## Python API

Use the high-level designer when you want the whole workflow in one class:

```python
from phasegrid import PhaseGridDesigner

designer = PhaseGridDesigner(
    library="examples/sweep.csv",
    phase="hyperbolic",
    aperture_radius=4.0,
    pitch=0.35,
    wavelength=0.532,
    focal_length=12.0,
    loss="phase_transmission",
    loss_params={"phase_weight": 1.0, "transmission_weight": 0.25},
    plot_structure=True,
    plot_phase=True,
    plot_propagation=True,
    backend="auto",
)

result = designer.run("design")
print(result.summary)
print(result.files)
```

Use a custom phase pattern:

```python
import math
from phasegrid import PhaseGridDesigner

def spiral_phase(x, y, params):
    return params["charge"] * math.atan2(y, x)

designer = PhaseGridDesigner(
    library="examples/sweep.csv",
    phase=spiral_phase,
    phase_params={"charge": 2},
    aperture_radius=4.0,
    pitch=0.35,
    loss="phase_only",
)
```

Use a custom loss:

```python
from phasegrid.library import phase_distance

def my_loss(target_phase, candidate, x, y, params):
    phase_loss = phase_distance(target_phase, candidate.phase) ** 2
    transmission_loss = 1 - candidate.transmission
    return phase_loss + 0.3 * transmission_loss
```

Lower-level fitting still works:

```python
from pathlib import Path

from phasegrid import PhaseFit

fit = PhaseFit.from_csv(
    "examples/sweep.csv",
    radius="radius_um",
    phase="phase_rad",
    transmission="transmission",
)

layout = fit.design_lens(
    wavelength=0.532,
    focal_length=12.0,
    aperture=8.0,
    pitch=0.35,
)

layout.to_csv("metalens_layout.csv")
fit.to_svg("phase_fit.svg")
```

The built-in `phase_only` and `phase_transmission` losses use the optional C++ selector when the extension is available. If it is not compiled, `backend="auto"` falls back to pure Python.

Compare many phase/loss/geometry settings:

```python
from phasegrid import PhaseGridSearch

search = PhaseGridSearch(
    library="examples/sweep.csv",
    sweep={
        "phase": ["hyperbolic", "parabolic", "vortex"],
        "loss": ["phase_only", "phase_transmission", "high_transmission"],
        "pitch": [0.25, 0.30, 0.35],
        "aperture_radius": [4.0, 6.0],
        "focal_length": [8.0, 12.0],
    },
    fixed={
        "wavelength": 0.532,
        "plot_structure": False,
        "plot_phase": False,
        "plot_propagation": False,
    },
)

result = search.run("search_out")
print(result.best.name, result.best.score)
```

This writes a ranked `leaderboard.csv` plus one folder per design.

Run the full pipeline: generate a unit-cell library, call a solver, search layouts, and rank them:

```python
from phasegrid import PhaseGridPipeline, linspace

pipeline = PhaseGridPipeline(
    library_sweep={
        "radius_um": linspace(0.05, 0.16, 24),
        "height_um": [0.6, 0.7],
        "period_um": [0.35],
        "wavelength_um": [0.532],
    },
    solver="mock",  # mock is dependency-free; replace with a custom RCWA/FDTD runner
    design_sweep={
        "phase": ["hyperbolic", "parabolic", "vortex"],
        "loss": ["phase_only", "phase_transmission"],
        "pitch": [0.30, 0.35, 0.40],
        "aperture_radius": [4.0],
        "focal_length": [8.0, 12.0],
    },
    fixed={"wavelength": 0.532},
)

result = pipeline.run("pipeline_out")
print(result.library_path)
print(result.search_result.best.name)
```

Use your own RCWA/FDTD code as the library solver:

```python
from phasegrid import PhaseGridPipeline

def run_unit_cell(job, out_dir, config):
    # job.params contains radius_um, height_um, period_um, wavelength_um, ...
    # Call Meep, S4, grcwa, Lumerical, or your own script here.
    return {
        "phase_rad": 1.23,
        "transmission": 0.82,
        "radius_um": job.params["radius_um"],
    }

pipeline = PhaseGridPipeline(
    library_sweep={"radius_um": [0.05, 0.06, 0.07]},
    solver_runner=run_unit_cell,
    design_sweep={
        "phase": ["hyperbolic"],
        "loss": ["phase_transmission"],
        "pitch": [0.35],
        "aperture_radius": [4.0],
        "focal_length": [12.0],
    },
    fixed={"wavelength": 0.532},
)
```

Attach your own FDTD runner when you want the design step to launch a near-field or propagation simulation:

```python
from phasegrid import PhaseGridDesigner

def run_meep(result, out_dir, config):
    # Write a Meep script, launch it, or call your existing simulation wrapper.
    # Return any serializable metadata you want recorded in fdtd/summary.json.
    return {"status": "queued", "mode": config["mode"]}

designer = PhaseGridDesigner(
    library="examples/sweep.csv",
    phase="hyperbolic",
    aperture_radius=4.0,
    pitch=0.35,
    wavelength=0.532,
    focal_length=12.0,
    run_fdtd=True,
    fdtd_runner=run_meep,
    fdtd_config={"mode": "near-field-and-propagation"},
)

designer.run("design_with_fdtd")
```

Generate a parameter sweep:

```python
from phasegrid import Sweep

sweep = Sweep(
    radius_um=[0.05, 0.06, 0.07, 0.08],
    height_um=[0.6, 0.7],
    wavelength_um=[0.532],
)

sweep.write("jobs")
```

This creates:

```text
jobs/
  manifest.csv
  job_0000/params.json
  job_0001/params.json
```

## CLI

Fit a sweep table:

```bash
phasegrid fit examples/sweep.csv --out phase_fit.svg
```

Design a metalens layout:

```bash
phasegrid design examples/sweep.csv \
  --wavelength 0.532 \
  --focal-length 12 \
  --aperture 8 \
  --pitch 0.35 \
  --out metalens_layout.csv
```

Generate sweep jobs:

```bash
phasegrid sweep --radius 0.05:0.12:0.01 --height 0.6,0.7 --wavelength 0.532 --out jobs
```

Compare design settings:

```bash
phasegrid compare examples/sweep.csv \
  --phase hyperbolic,parabolic,vortex \
  --loss phase_only,phase_transmission \
  --pitch 0.25,0.3,0.35 \
  --aperture-radius 4,6 \
  --wavelength 0.532 \
  --focal-length 8,12 \
  --out search_out
```

Run a dependency-free full pipeline demo:

```bash
phasegrid pipeline-demo --out pipeline_out
```

Pipeline output:

```text
pipeline_out/
  library_jobs/
  library_results/library.csv
  search/leaderboard.csv
  pipeline_summary.json
```

## Input Sweep Format

At minimum, provide radius and phase columns:

```csv
radius_um,phase_rad,transmission
0.05,0.10,0.42
0.06,0.62,0.58
0.07,1.31,0.71
```

Phase values can be wrapped or unwrapped. `phasegrid` unwraps and normalizes the curve internally.

## Output Layout Format

`design_lens` writes one row per lattice site:

```csv
x_um,y_um,r_um,target_phase_rad,fit_phase_rad,phase_error_rad,transmission
```

The result can feed a Meep/Lumerical script, a GDS pipeline, or a quick design sanity check.
