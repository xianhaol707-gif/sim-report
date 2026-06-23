from pathlib import Path

from meep_report.parameters import collect_parameters, parse_simple_yaml


def test_parse_simple_yaml_nested_scalars() -> None:
    parsed = parse_simple_yaml(
        """
        simulation:
          resolution: 40
          enabled: true
        material: TiO2
        """
    )

    assert parsed == {"simulation": {"resolution": 40, "enabled": True}, "material": "TiO2"}


def test_collect_parameters_from_json_and_python(tmp_path: Path) -> None:
    results = tmp_path / "results"
    results.mkdir()
    params = results / "params.json"
    script = results / "run.py"
    params.write_text('{"mesh": {"dx": 0.02}}', encoding="utf-8")
    script.write_text('resolution = 50\nmaterial = "Si"\nignored = object()\n', encoding="utf-8")

    rows = collect_parameters(results, [params], [script])

    values = {(row.source, row.name): row.value for row in rows}
    assert values[("params.json", "mesh.dx")] == "0.02"
    assert values[("run.py", "resolution")] == "50"
    assert values[("run.py", "material")] == "Si"

