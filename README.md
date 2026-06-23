# meep-report

Generate a clean Markdown report from Meep/FDTD simulation results.

`meep-report` is designed for photonics and metalens workflows where every run leaves behind a mix of parameters, CSV metrics, field images, HDF5 files, and logs. It turns that folder into a readable report with figures, tables, and reproducibility notes.

## What It Creates

```text
report/
  summary.md
  parameters.csv
  metrics.csv
  datasets.csv
  charts/
    metrics_transmission.svg
  figures/
    focal_intensity.png
```

## Quick Start

```bash
python -m pip install --no-build-isolation .
meep-report path/to/results --out report --title "TiO2 dual metalens"
```

For local development:

```bash
PYTHONPATH=src python -m meep_report examples/basic/results --out examples/basic/report
```

## Supported Inputs

- `*.json`, `*.yaml`, `*.yml`: flattened into `parameters.csv`.
- `*.py`, `*.ctl`: simple scalar assignments are extracted as run parameters.
- `*.csv`, `*.tsv`, `*.dat`: numeric columns are collected into `metrics.csv` and plotted as SVG charts.
- `*.png`, `*.jpg`, `*.jpeg`, `*.svg`, `*.tif`, `*.tiff`: copied into `figures/` and embedded in `summary.md`.
- `*.h5`, `*.hdf5`: summarized in `datasets.csv` when `h5py` is installed; otherwise listed as HDF5 assets.
- `*.log`, `*.out`, `*.err`, `*.txt`: scanned for common warnings, errors, and completion hints.

## CLI

```bash
meep-report RESULTS_DIR --out report
```

Options:

```text
--title TEXT           Report title.
--max-charts N         Maximum generated SVG charts. Default: 60.
--max-figures N        Maximum embedded figure previews. Default: 30.
--copy-figures / --no-copy-figures
--strict               Fail when the input folder has no recognizable result files.
```

## Why This Exists

Meep/FDTD runs are easy to generate and hard to review later. This tool focuses on the boring but important parts:

- Which parameters produced this run?
- What figures and field plots came out?
- Which CSV metrics changed?
- Did logs contain warnings or failures?
- Which HDF5 datasets were produced?

The output is plain Markdown plus CSV and SVG files, so it works on GitHub, clusters, and lab notebooks without a database server.

## Example

```bash
PYTHONPATH=src python -m meep_report examples/basic/results --out /tmp/meep-report-demo
```

Open `/tmp/meep-report-demo/summary.md` to inspect the generated report.

