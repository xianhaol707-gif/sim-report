from phasegrid import Channel, PhaseGridDesigner


def test_dualband_dynamic_selects_from_multichannel_library(tmp_path) -> None:
    designer = PhaseGridDesigner(
        library="examples/dualband_pb.csv",
        phase="hyperbolic",
        channels=[
            {
                "name": "532",
                "phase_col": "phase_532",
                "transmission_col": "T_532",
                "phase": "hyperbolic",
                "phase_params": {"wavelength": 0.532, "focal_length": 12.0},
                "weight": 1.0,
            },
            {
                "name": "633",
                "phase_col": "phase_633",
                "transmission_col": "T_633",
                "phase": "hyperbolic",
                "phase_params": {"wavelength": 0.633, "focal_length": 14.0},
                "weight": 1.0,
            },
        ],
        loss="dualband",
        aperture_radius=0.5,
        pitch=0.5,
        phase_mode="dynamic",
        plot_structure=False,
        plot_phase=False,
        plot_propagation=False,
    )

    result = designer.run(tmp_path)
    layout = result.files["layout"].read_text(encoding="utf-8")

    assert result.summary["channels"] == 2
    assert "target_phase_532" in layout
    assert "phase_error_633" in layout
    assert result.sites[0].candidate.shape == "rect"


def test_pb_phase_outputs_rotation(tmp_path) -> None:
    designer = PhaseGridDesigner(
        library="examples/dualband_pb.csv",
        phase="hyperbolic",
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
        aperture_radius=0.5,
        pitch=0.5,
        phase_mode="pb",
        rotation_steps=12,
        plot_structure=False,
        plot_phase=False,
        plot_propagation=False,
    )

    result = designer.run(tmp_path)
    layout = result.files["layout"].read_text(encoding="utf-8")

    assert "rotation_deg" in layout
    assert any(site.candidate.rotation is not None for site in result.sites)

