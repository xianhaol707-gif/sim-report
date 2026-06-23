from __future__ import annotations

from pathlib import Path

from .models import DatasetSummary


def summarize_hdf5(results_dir: Path, hdf5_files: list[Path]) -> list[DatasetSummary]:
    try:
        import h5py  # type: ignore
    except ModuleNotFoundError:
        return [
            DatasetSummary(
                source=path.relative_to(results_dir).as_posix(),
                dataset="",
                shape="h5py not installed",
                dtype="",
            )
            for path in hdf5_files
        ]

    rows: list[DatasetSummary] = []
    for path in hdf5_files:
        source = path.relative_to(results_dir).as_posix()
        try:
            with h5py.File(path, "r") as handle:
                handle.visititems(lambda name, obj: append_dataset(rows, source, name, obj))
        except OSError as exc:
            rows.append(DatasetSummary(source, "", f"unreadable: {exc}", ""))
    return rows


def append_dataset(rows: list[DatasetSummary], source: str, name: str, obj: object) -> None:
    if not hasattr(obj, "shape") or not hasattr(obj, "dtype"):
        return
    shape = "x".join(str(part) for part in getattr(obj, "shape", ())) or "scalar"
    dtype = str(getattr(obj, "dtype", ""))
    minimum = maximum = mean = ""
    try:
        if getattr(obj, "size", 0) and getattr(obj, "size", 0) <= 5_000_000:
            data = obj[()]
            minimum = f"{data.min():.6g}"
            maximum = f"{data.max():.6g}"
            mean = f"{data.mean():.6g}"
    except Exception:
        pass
    rows.append(DatasetSummary(source, name, shape, dtype, minimum, maximum, mean))

