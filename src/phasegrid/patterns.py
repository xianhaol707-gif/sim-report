from __future__ import annotations

import math
from typing import Callable

from .fit import TAU

PhaseCallable = Callable[[float, float, dict[str, float]], float]


def resolve_phase(pattern: str | PhaseCallable) -> PhaseCallable:
    if callable(pattern):
        return pattern
    patterns = {
        "flat": flat,
        "hyperbolic": hyperbolic,
        "lens": hyperbolic,
        "parabolic": parabolic,
        "vortex": vortex,
        "grating": grating,
        "axicon": axicon,
    }
    try:
        return patterns[pattern.lower()]
    except KeyError as exc:
        raise ValueError(f"Unknown phase pattern: {pattern}") from exc


def flat(x: float, y: float, params: dict[str, float]) -> float:
    return params.get("phase", 0.0) % TAU


def hyperbolic(x: float, y: float, params: dict[str, float]) -> float:
    wavelength = required(params, "wavelength")
    focal_length = required(params, "focal_length")
    r = math.hypot(x, y)
    return (-(TAU / wavelength) * (math.sqrt(r * r + focal_length * focal_length) - focal_length)) % TAU


def parabolic(x: float, y: float, params: dict[str, float]) -> float:
    wavelength = required(params, "wavelength")
    focal_length = required(params, "focal_length")
    return (-(math.pi / (wavelength * focal_length)) * (x * x + y * y)) % TAU


def vortex(x: float, y: float, params: dict[str, float]) -> float:
    charge = params.get("charge", 1.0)
    return (charge * math.atan2(y, x)) % TAU


def grating(x: float, y: float, params: dict[str, float]) -> float:
    period = required(params, "period")
    angle = params.get("angle", 0.0)
    coordinate = x * math.cos(angle) + y * math.sin(angle)
    return (TAU * coordinate / period) % TAU


def axicon(x: float, y: float, params: dict[str, float]) -> float:
    period = required(params, "period")
    return (TAU * math.hypot(x, y) / period) % TAU


def required(params: dict[str, float], key: str) -> float:
    if key not in params:
        raise ValueError(f"phase pattern requires {key!r}")
    return params[key]

