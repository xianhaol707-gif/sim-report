from pathlib import Path

from sim_report.report import build_report, parse_simple_yaml, read_numeric_table


def test_build_report_generates_summary_parameters_and_charts(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    (results / "metrics.csv").write_text("step,loss,accuracy\n0,1.0,0.1\n1,0.6,0.4\n2,0.3,0.8\n", encoding="utf-8")
    (results / "params.json").write_text('{"solver": {"dx": 0.02}, "epochs": 3}', encoding="utf-8")

    output = tmp_path / "report"
    report = build_report(results, output, title="Test report")

    assert report.summary_path.exists()
    assert report.parameters_path.exists()
    assert len(report.chart_paths) == 2
    assert "solver.dx" in report.parameters_path.read_text(encoding="utf-8")
    assert "![metrics_loss]" in report.summary_path.read_text(encoding="utf-8")


def test_read_numeric_table_uses_first_numeric_column_as_x(tmp_path: Path) -> None:
    table = tmp_path / "metrics.tsv"
    table.write_text("time\tfield\n0\t2\n2\t6\n", encoding="utf-8")

    series = read_numeric_table(table)

    assert series["field"] == [(0.0, 2.0), (2.0, 6.0)]


def test_parse_simple_yaml_supports_nested_values() -> None:
    parsed = parse_simple_yaml(
        """
        material:
          index: 2.4
          enabled: true
        name: demo
        """
    )

    assert parsed == {"material": {"index": 2.4, "enabled": True}, "name": "demo"}

