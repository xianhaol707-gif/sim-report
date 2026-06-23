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
