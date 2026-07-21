import json

from phasegrid import benchmark_selector, compare_backends
from phasegrid.benchmark import write_benchmark_json


def test_benchmark_selector_python_backend() -> None:
    result = benchmark_selector(sites=3, candidates=4, channels=2, rotation_steps=5, backend="python")

    assert result.status == "ok"
    assert result.selections == 120
    assert result.elapsed_seconds >= 0
    assert result.selections_per_second >= 0


def test_benchmark_json_output(tmp_path) -> None:
    results = compare_backends(sites=2, candidates=3, channels=1, rotation_steps=4, backends=["python"])
    path = write_benchmark_json(tmp_path / "bench.json", results)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["backend"] == "python"
    assert data[0]["status"] == "ok"

