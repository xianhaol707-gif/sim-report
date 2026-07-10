import json

import pytest

from phasegrid import PillarLibrary


def test_library_report_infers_phase_and_transmission_columns() -> None:
    library = PillarLibrary.from_csv("examples/dualband_pb.csv")

    report = library.report()

    assert report.candidates == 6
    assert report.shapes == {"rect": 6}
    assert "phase_532" in report.phase
    assert "phase_633" in report.phase
    assert "T_532" in report.transmission
    assert report.phase["phase_532"].covers_2pi is False


def test_library_report_writes_json_and_markdown(tmp_path) -> None:
    library = PillarLibrary.from_csv("examples/sweep.csv")
    report = library.report(required_columns=["radius_um", "phase_rad"])

    json_path = report.to_json(tmp_path / "report.json")
    markdown_path = report.to_markdown(tmp_path / "report.md")

    assert json.loads(json_path.read_text(encoding="utf-8"))["candidates"] == 12
    assert "Phase Columns" in markdown_path.read_text(encoding="utf-8")


def test_library_validate_fails_for_missing_column() -> None:
    library = PillarLibrary.from_csv("examples/sweep.csv")

    with pytest.raises(ValueError, match="missing_col"):
        library.validate(required_columns=["missing_col"], require_2pi=False)

