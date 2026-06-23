from __future__ import annotations

from .library import PillarLibrary, phase_distance


def select_indices(
    target_phases: list[float],
    library: PillarLibrary,
    phase_weight: float,
    transmission_weight: float,
    backend: str = "auto",
) -> list[int]:
    if backend in {"auto", "cpp"}:
        try:
            from phasegrid import _phasegrid_cpp  # type: ignore

            return list(
                _phasegrid_cpp.select_weighted(
                    target_phases,
                    library.phases,
                    library.transmissions,
                    phase_weight,
                    transmission_weight,
                )
            )
        except Exception:
            if backend == "cpp":
                raise
    return select_indices_python(target_phases, library, phase_weight, transmission_weight)


def select_indices_python(
    target_phases: list[float],
    library: PillarLibrary,
    phase_weight: float,
    transmission_weight: float,
) -> list[int]:
    indices: list[int] = []
    for target in target_phases:
        best_index = 0
        best_loss = float("inf")
        for index, candidate in enumerate(library.candidates):
            phase_error = phase_distance(target, candidate.phase)
            transmission_loss = 1.0 - candidate.transmission
            loss = phase_weight * phase_error * phase_error + transmission_weight * transmission_loss * transmission_loss
            if loss < best_loss:
                best_loss = loss
                best_index = index
        indices.append(best_index)
    return indices

