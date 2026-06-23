import math
from pathlib import Path

from phasegrid import PhaseFit, PhaseSample


def test_radius_for_phase_interpolates() -> None:
    fit = PhaseFit([PhaseSample(0.1, 0.0, 0.5), PhaseSample(0.2, math.pi, 0.9)])

    sample = fit.radius_for_phase(math.pi / 2)

    assert round(sample.radius, 6) == 0.15
    assert round(sample.transmission or 0.0, 6) == 0.7


def test_design_lens_writes_layout(tmp_path: Path) -> None:
    fit = PhaseFit(
        [
            PhaseSample(0.05, 0.0),
            PhaseSample(0.08, 1.5),
            PhaseSample(0.11, 3.0),
            PhaseSample(0.14, 4.5),
            PhaseSample(0.17, 6.2),
        ]
    )

    layout = fit.design_lens(wavelength=0.532, focal_length=12.0, aperture=1.0, pitch=0.5)
    path = layout.to_csv(tmp_path / "layout.csv")

    assert path.exists()
    assert len(layout.points) == 5
    assert "x_um,y_um,r_um" in path.read_text(encoding="utf-8")

