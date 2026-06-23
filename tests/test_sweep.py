import csv

from phasegrid import Sweep
from phasegrid.sweep import parse_values


def test_parse_values_range_and_list() -> None:
    assert parse_values("0.1:0.3:0.1") == [0.1, 0.2, 0.3]
    assert parse_values("a,b") == ["a", "b"]


def test_sweep_writes_jobs(tmp_path) -> None:
    jobs = Sweep(radius_um=[0.05, 0.06], height_um=[0.6], wavelength_um=[0.532]).write(tmp_path)

    assert len(jobs) == 2
    assert (tmp_path / "job_0000" / "params.json").exists()
    with (tmp_path / "manifest.csv").open("r", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["job", "radius_um", "height_um", "wavelength_um"]

