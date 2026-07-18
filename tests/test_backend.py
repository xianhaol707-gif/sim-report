from phasegrid import Channel, PhaseGridDesigner


def test_multichannel_python_backend_is_deterministic(tmp_path) -> None:
    designer = PhaseGridDesigner(
        library="examples/dualband_pb.csv",
        channels=[
            {
                "name": "532",
                "phase_col": "phase_532",
                "transmission_col": "T_532",
                "phase": "hyperbolic",
                "phase_params": {"wavelength": 0.532, "focal_length": 12.0},
            },
            {
                "name": "633",
                "phase_col": "phase_633",
                "transmission_col": "T_633",
                "phase": "hyperbolic",
                "phase_params": {"wavelength": 0.633, "focal_length": 14.0},
            },
        ],
        loss="dualband",
        aperture_radius=0.5,
        pitch=0.5,
        backend="python",
        plot_structure=False,
        plot_phase=False,
        plot_propagation=False,
    )

    result = designer.run(tmp_path)

    assert len(result.sites) == 5
    assert all(site.candidate.shape == "rect" for site in result.sites)


def test_multichannel_pb_python_backend_selects_rotation(tmp_path) -> None:
    designer = PhaseGridDesigner(
        library="examples/dualband_pb.csv",
        channels=[
            Channel(
                name="532",
                phase_col="phase_532",
                transmission_col="T_532",
                phase="hyperbolic",
                phase_params={"wavelength": 0.532, "focal_length": 12.0},
            )
        ],
        loss="pb_phase",
        use_pb=True,
        rotation_steps=12,
        aperture_radius=0.5,
        pitch=0.5,
        backend="python",
        plot_structure=False,
        plot_phase=False,
        plot_propagation=False,
    )

    result = designer.run(tmp_path)

    assert any(site.candidate.rotation is not None for site in result.sites)
