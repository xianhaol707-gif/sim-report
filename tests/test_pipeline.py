from phasegrid import PhaseGridPipeline, arange, linspace


def test_pipeline_mock_solver_writes_library_and_search(tmp_path) -> None:
    pipeline = PhaseGridPipeline(
        library_sweep={
            "radius_um": linspace(0.05, 0.16, 6),
            "height_um": [0.6],
            "wavelength_um": [0.532],
        },
        solver="mock",
        design_sweep={
            "phase": ["hyperbolic", "parabolic"],
            "loss": ["phase_only"],
            "pitch": [0.35],
            "aperture_radius": [0.7],
            "focal_length": [12.0],
        },
        fixed={"wavelength": 0.532, "plot_structure": False, "plot_phase": False, "plot_propagation": False},
    )

    result = pipeline.run(tmp_path)

    assert result.library_path.exists()
    assert result.search_result.leaderboard_path.exists()
    assert result.summary_path.exists()
    assert len(result.search_result.runs) == 2
    assert "phase_rad" in result.library_path.read_text(encoding="utf-8")


def test_pipeline_custom_solver_and_validation(tmp_path) -> None:
    validations = []

    def solver(job, out_dir, config):
        radius = float(job.params["radius_um"])
        return {
            "radius_um": radius,
            "phase_rad": radius * 40,
            "transmission": 0.8,
        }

    def validate(result, out_dir, config):
        validations.append(len(result.sites))
        return {"status": "ok", "sites": len(result.sites)}

    pipeline = PhaseGridPipeline(
        library_sweep={"radius_um": arange(0.05, 0.09, 0.02)},
        solver_runner=solver,
        design_sweep={
            "phase": ["flat"],
            "loss": ["phase_only"],
            "pitch": [0.5],
            "aperture_radius": [0.5],
        },
        fixed={"phase_params": {"phase": 0.0}, "plot_structure": False, "plot_phase": False, "plot_propagation": False},
        validate_best=1,
        validation_runner=validate,
    )

    result = pipeline.run(tmp_path)

    assert validations == [5]
    assert result.files["validation_1"].exists()

