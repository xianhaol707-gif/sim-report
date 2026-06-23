from pathlib import Path

from meep_report.metrics import read_numeric_series


def test_read_numeric_series_from_csv() -> None:
    path = Path("metrics.csv")
    tmp = path
    tmp.write_text("freq,transmission\n1.0,0.2\n1.5,0.6\n", encoding="utf-8")
    try:
        series = read_numeric_series(tmp)
    finally:
        tmp.unlink()

    assert series["transmission"] == [(1.0, 0.2), (1.5, 0.6)]


def test_read_numeric_series_from_dat(tmp_path: Path) -> None:
    path = tmp_path / "flux.dat"
    path.write_text("# freq refl\n1.0 0.1\n2.0 0.3\n", encoding="utf-8")

    series = read_numeric_series(path)

    assert series["col_1"] == [(1.0, 0.1), (2.0, 0.3)]

