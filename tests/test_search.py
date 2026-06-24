from phasegrid import PhaseGridSearch


def test_search_writes_leaderboard(tmp_path) -> None:
    search = PhaseGridSearch(
        library="examples/sweep.csv",
        sweep={
            "phase": ["hyperbolic", "parabolic"],
            "loss": ["phase_only", "phase_transmission"],
            "pitch": [0.35],
            "aperture_radius": [0.7],
            "wavelength": [0.532],
            "focal_length": [12.0],
        },
        fixed={"plot_structure": False, "plot_phase": False, "plot_propagation": False, "backend": "python"},
    )

    result = search.run(tmp_path)

    assert len(result.runs) == 4
    assert result.leaderboard_path.exists()
    assert result.best.score <= result.runs[-1].score
    text = result.leaderboard_path.read_text(encoding="utf-8")
    assert "mean_abs_phase_error_rad" in text


def test_search_accepts_multichannel_pb_settings(tmp_path) -> None:
    search = PhaseGridSearch(
        library="examples/dualband_pb.csv",
        sweep={
            "phase_mode": ["pb"],
            "loss": ["pb_phase"],
            "pitch": [0.5],
            "aperture_radius": [0.5],
            "rotation_steps": [12],
        },
        fixed={
            "channels": [
                {
                    "name": "532",
                    "phase_col": "phase_532",
                    "transmission_col": "T_532",
                    "phase": "hyperbolic",
                    "phase_params": {"wavelength": 0.532, "focal_length": 12.0},
                }
            ],
            "plot_structure": False,
            "plot_phase": False,
            "plot_propagation": False,
        },
    )

    result = search.run(tmp_path)

    assert len(result.runs) == 1
    assert result.best.result.summary["phase_mode"] == "pb"


def test_search_can_sweep_use_pb(tmp_path) -> None:
    search = PhaseGridSearch(
        library="examples/dualband_pb.csv",
        sweep={
            "use_pb": [False, True],
            "loss": ["pb_phase"],
            "pitch": [0.5],
            "aperture_radius": [0.5],
            "rotation_steps": [12],
        },
        fixed={
            "channels": [
                {
                    "name": "532",
                    "phase_col": "phase_532",
                    "transmission_col": "T_532",
                    "phase": "hyperbolic",
                    "phase_params": {"wavelength": 0.532, "focal_length": 12.0},
                }
            ],
            "plot_structure": False,
            "plot_phase": False,
            "plot_propagation": False,
        },
    )

    result = search.run(tmp_path)

    modes = {run.result.summary["phase_mode"] for run in result.runs}
    assert modes == {"dynamic", "hybrid"}
