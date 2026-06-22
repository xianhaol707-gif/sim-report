# sim-report

`sim-report` reads a simulation `results/` folder and generates:

- `summary.md`
- `parameters.csv`
- SVG charts for numeric CSV/TSV files

It uses only the Python standard library, so it works well on remote compute nodes and lightweight environments.

## Install

```bash
python -m pip install .
```

On offline machines that already have `setuptools`, use:

```bash
python -m pip install --no-build-isolation .
```

For local development, you can run it without installation:

```bash
PYTHONPATH=src python -m sim_report results --out report
```

## Usage

```bash
sim-report path/to/results --out path/to/report
```

Useful options:

```bash
sim-report results --out report --title "FDTD run" --max-charts 30
```

The tool scans recursively for:

- CSV/TSV numeric tables and creates line charts for numeric columns.
- JSON metadata and simple key/value YAML files, then flattens values into `parameters.csv`.
- Images and text logs, then lists them in `summary.md`.

## Output

```text
report/
  summary.md
  parameters.csv
  charts/
    example_metric.svg
```

`summary.md` links to generated charts and includes a compact inventory of detected files.
