from __future__ import annotations

from .channels import Channel
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


def select_multichannel(
    target_rows: list[list[float]],
    phase_rows: list[list[float]],
    transmission_rows: list[list[float]],
    channel_weights: list[float],
    transmission_weights: list[float],
    pb_spins: list[int],
    phase_weight: float,
    phase_mode: str,
    rotation_steps: int,
    pb_spin: int,
    backend: str = "auto",
) -> list[tuple[int, int | None]]:
    if backend in {"auto", "cpp"}:
        try:
            from phasegrid import _phasegrid_cpp  # type: ignore

            packed = _phasegrid_cpp.select_multichannel(
                flatten(target_rows),
                flatten(phase_rows),
                flatten(transmission_rows),
                channel_weights,
                transmission_weights,
                [float(spin) for spin in pb_spins],
                len(target_rows),
                len(phase_rows),
                len(channel_weights),
                phase_weight,
                phase_mode,
                rotation_steps,
                pb_spin,
            )
            return [(int(candidate), None if int(rotation) < 0 else int(rotation)) for candidate, rotation in packed]
        except Exception:
            if backend == "cpp":
                raise
    return select_multichannel_python(
        target_rows,
        phase_rows,
        transmission_rows,
        channel_weights,
        transmission_weights,
        pb_spins,
        phase_weight,
        phase_mode,
        rotation_steps,
        pb_spin,
    )


def select_multichannel_from_library(
    target_rows: list[list[float]],
    library: PillarLibrary,
    channels: list[Channel],
    phase_weight: float,
    phase_mode: str,
    rotation_steps: int,
    pb_spin: int,
    backend: str = "auto",
) -> list[tuple[int, int | None]]:
    phase_rows = [
        [candidate.phase_for(channel.phase_col) for channel in channels]
        for candidate in library.candidates
    ]
    transmission_rows = [
        [candidate.transmission_for(channel.transmission_col) for channel in channels]
        for candidate in library.candidates
    ]
    return select_multichannel(
        target_rows=target_rows,
        phase_rows=phase_rows,
        transmission_rows=transmission_rows,
        channel_weights=[channel.weight for channel in channels],
        transmission_weights=[channel.transmission_weight for channel in channels],
        pb_spins=[channel.pb_spin for channel in channels],
        phase_weight=phase_weight,
        phase_mode=phase_mode,
        rotation_steps=rotation_steps,
        pb_spin=pb_spin,
        backend=backend,
    )


def select_multichannel_python(
    target_rows: list[list[float]],
    phase_rows: list[list[float]],
    transmission_rows: list[list[float]],
    channel_weights: list[float],
    transmission_weights: list[float],
    pb_spins: list[int],
    phase_weight: float,
    phase_mode: str,
    rotation_steps: int,
    pb_spin: int,
) -> list[tuple[int, int | None]]:
    use_rotation = phase_mode in {"pb", "hybrid"}
    theta_count = rotation_steps if use_rotation else 1
    results: list[tuple[int, int | None]] = []
    for targets in target_rows:
        best_candidate = 0
        best_rotation: int | None = None
        best_loss = float("inf")
        for candidate_index, phases in enumerate(phase_rows):
            transmissions = transmission_rows[candidate_index]
            for rotation_index in range(theta_count):
                theta = rotation_index * 3.141592653589793 / rotation_steps if use_rotation else 0.0
                loss = multichannel_loss(
                    targets,
                    phases,
                    transmissions,
                    channel_weights,
                    transmission_weights,
                    pb_spins,
                    phase_weight,
                    phase_mode,
                    pb_spin,
                    theta,
                )
                if loss < best_loss:
                    best_loss = loss
                    best_candidate = candidate_index
                    best_rotation = rotation_index if use_rotation else None
        results.append((best_candidate, best_rotation))
    return results


def multichannel_loss(
    targets: list[float],
    phases: list[float],
    transmissions: list[float],
    channel_weights: list[float],
    transmission_weights: list[float],
    pb_spins: list[int],
    phase_weight: float,
    phase_mode: str,
    pb_spin: int,
    theta: float,
) -> float:
    total = 0.0
    for index, target in enumerate(targets):
        pb_phase = 2.0 * pb_spins[index] * pb_spin * theta
        if phase_mode == "pb":
            realized = pb_phase
        elif phase_mode == "hybrid":
            realized = phases[index] + pb_phase
        else:
            realized = phases[index]
        error = phase_distance(target, realized)
        transmission_loss = 1.0 - transmissions[index]
        total += channel_weights[index] * phase_weight * error * error
        total += transmission_weights[index] * transmission_loss * transmission_loss
    return total


def flatten(rows: list[list[float]]) -> list[float]:
    return [value for row in rows for value in row]
