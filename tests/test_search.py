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

