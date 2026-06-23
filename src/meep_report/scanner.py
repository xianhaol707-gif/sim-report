from __future__ import annotations

from pathlib import Path

from .models import Inventory


PARAMETER_EXTENSIONS = {".json", ".yaml", ".yml"}
TABLE_EXTENSIONS = {".csv", ".tsv", ".dat"}
FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".tif", ".tiff"}
HDF5_EXTENSIONS = {".h5", ".hdf5"}
LOG_EXTENSIONS = {".log", ".out", ".err", ".txt"}
SCRIPT_EXTENSIONS = {".py", ".ctl"}


def scan_results(results_dir: Path) -> Inventory:
    inventory = Inventory()
    for path in sorted(results_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in PARAMETER_EXTENSIONS:
            inventory.parameters.append(path)
        elif suffix in TABLE_EXTENSIONS:
            inventory.tables.append(path)
        elif suffix in FIGURE_EXTENSIONS:
            inventory.figures.append(path)
        elif suffix in HDF5_EXTENSIONS:
            inventory.hdf5.append(path)
        elif suffix in LOG_EXTENSIONS:
            inventory.logs.append(path)
        elif suffix in SCRIPT_EXTENSIONS:
            inventory.scripts.append(path)
        else:
            inventory.other.append(path)
    return inventory

