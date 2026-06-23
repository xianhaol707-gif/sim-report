from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Channel:
    name: str
    phase_col: str
    transmission_col: str = "transmission"
    phase: str | Any = "hyperbolic"
    phase_params: dict[str, float] | None = None
    weight: float = 1.0
    transmission_weight: float = 0.2
    pb_spin: int = 1


def normalize_channels(channels: list[dict[str, Any] | Channel] | None, default_phase: str | Any, default_phase_params: dict[str, float]) -> list[Channel]:
    if not channels:
        return [
            Channel(
                name="default",
                phase_col="phase_rad",
                transmission_col="transmission",
                phase=default_phase,
                phase_params=dict(default_phase_params),
            )
        ]
    normalized = []
    for index, channel in enumerate(channels):
        if isinstance(channel, Channel):
            normalized.append(channel)
            continue
        name = str(channel.get("name", f"ch{index}"))
        normalized.append(
            Channel(
                name=name,
                phase_col=str(channel.get("phase_col", f"phase_{name}")),
                transmission_col=str(channel.get("transmission_col", channel.get("T_col", f"T_{name}"))),
                phase=channel.get("phase", default_phase),
                phase_params=dict(channel.get("phase_params", default_phase_params)),
                weight=float(channel.get("weight", 1.0)),
                transmission_weight=float(channel.get("transmission_weight", 0.2)),
                pb_spin=int(channel.get("pb_spin", 1)),
            )
        )
    return normalized

