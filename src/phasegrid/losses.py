from __future__ import annotations

from typing import Callable

from .library import PillarCandidate, phase_distance

LossCallable = Callable[[float, PillarCandidate, float, float, dict[str, float]], float]


def resolve_loss(loss: str | LossCallable) -> LossCallable:
    if callable(loss):
        return loss
    losses = {
        "phase_only": phase_only,
        "phase": phase_only,
        "phase_transmission": phase_transmission,
        "balanced": phase_transmission,
        "high_transmission": high_transmission,
        "dualband": phase_transmission,
        "multiband": phase_transmission,
        "pb": phase_transmission,
        "pb_phase": phase_transmission,
        "pb_dualband": phase_transmission,
        "pb_multiband": phase_transmission,
    }
    try:
        return losses[loss.lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown loss function: {loss}") from exc


def phase_only(target_phase: float, candidate: PillarCandidate, x: float, y: float, params: dict[str, float]) -> float:
    phase_weight = params.get("phase_weight", 1.0)
    error = phase_distance(target_phase, candidate.phase)
    return phase_weight * error * error


def phase_transmission(target_phase: float, candidate: PillarCandidate, x: float, y: float, params: dict[str, float]) -> float:
    phase_weight = params.get("phase_weight", 1.0)
    transmission_weight = params.get("transmission_weight", 0.2)
    error = phase_distance(target_phase, candidate.phase)
    transmission_loss = 1.0 - candidate.transmission
    return phase_weight * error * error + transmission_weight * transmission_loss * transmission_loss


def high_transmission(target_phase: float, candidate: PillarCandidate, x: float, y: float, params: dict[str, float]) -> float:
    phase_weight = params.get("phase_weight", 0.3)
    transmission_weight = params.get("transmission_weight", 1.0)
    error = phase_distance(target_phase, candidate.phase)
    transmission_loss = 1.0 - candidate.transmission
    return phase_weight * error * error + transmission_weight * transmission_loss * transmission_loss
