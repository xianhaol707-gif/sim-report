import math

from phasegrid import PhaseGridDesigner
from phasegrid.library import phase_distance


def test_designer_writes_layout_and_plots(tmp_path) -> None:
    designer = PhaseGridDesigner(
        library="examples/sweep.csv",
        phase="hyperbolic",
        aperture_radius=0.7,
        pitch=0.35,
        wavelength=0.532,
        focal_length=12.0,
        plot_structure=True,
        plot_phase=True,
        plot_propagation=True,
        propagation_size=18,
        backend="python",
    )

    result = designer.run(tmp_path)

    assert result.files["layout"].exists()
    assert result.files["structure"].exists()
    assert result.files["phase"].exists()
    assert result.files["propagation"].exists()
    assert result.summary["sites"] == 13


def test_designer_accepts_custom_phase_and_loss(tmp_path) -> None:
    def phase(x: float, y: float, params: dict[str, float]) -> float:
        return params["charge"] * math.atan2(y, x)

    def loss(target_phase, candidate, x, y, params):
        return phase_distance(target_phase, candidate.phase) ** 2 + 0.1 * (1 - candidate.transmission)

    designer = PhaseGridDesigner(
        library="examples/sweep.csv",
        phase=phase,
        phase_params={"charge": 1.0},
        loss=loss,
        aperture_radius=0.5,
        pitch=0.5,
        plot_structure=False,
        plot_phase=False,
        plot_propagation=False,
    )

    result = designer.run(tmp_path)

    assert result.files["layout"].exists()
    assert "structure" not in result.files
    assert result.summary["phase"] == "custom"
    assert result.summary["loss"] == "custom"


def test_designer_fdtd_hook(tmp_path) -> None:
    calls = []

    def runner(result, out_dir, config):
        calls.append((len(result.sites), out_dir, config["mode"]))
        (out_dir / "near_field.csv").write_text("x,y,intensity\n0,0,1\n", encoding="utf-8")
        return {"status": "ok", "near_field": "near_field.csv"}

    designer = PhaseGridDesigner(
        library="examples/sweep.csv",
        phase="hyperbolic",
        aperture_radius=0.5,
        pitch=0.5,
        wavelength=0.532,
        focal_length=12.0,
        plot_structure=False,
        plot_phase=False,
        plot_propagation=False,
        run_fdtd=True,
        fdtd_runner=runner,
        fdtd_config={"mode": "near-field"},
    )

    result = designer.run(tmp_path)

    assert calls[0][0] == 5
    assert result.summary["fdtd_status"] == "ok"
    assert result.files["fdtd_summary"].exists()
