from pathlib import Path

from meep_report import ReportOptions, build_report


def test_build_report_outputs_core_files(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    (results / "params.json").write_text('{"wavelength": 0.532}', encoding="utf-8")
    (results / "metrics.csv").write_text("step,power\n0,0.1\n1,0.4\n2,0.8\n", encoding="utf-8")
    (results / "run.log").write_text("warning: test\nSimulation complete\n", encoding="utf-8")

    output = tmp_path / "report"
    report = build_report(results, output, ReportOptions(title="Demo"))

    assert report.summary_path.exists()
    assert report.parameters_path.exists()
    assert report.metrics_path.exists()
    assert report.datasets_path.exists()
    assert len(report.chart_paths) == 1
    summary = report.summary_path.read_text(encoding="utf-8")
    assert "# Demo" in summary
    assert "wavelength" in summary
    assert "warning: test" in summary
