from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from .backend import select_indices
from .channels import Channel, normalize_channels
from .fit import TAU, wrap_phase
from .library import PillarCandidate, PillarLibrary, phase_distance
from .losses import LossCallable, resolve_loss
from .patterns import PhaseCallable, resolve_phase
from .plots import plot_phase, plot_propagation, plot_structure


@dataclass(frozen=True)
class DesignSite:
    x: float
    y: float
    target_phase: float
    candidate: PillarCandidate
    loss: float
    channel_targets: dict[str, float] | None = None
    channel_errors: dict[str, float] | None = None


@dataclass(frozen=True)
class DesignResult:
    sites: list[DesignSite]
    files: dict[str, Path]
    summary: dict[str, float | int | str]

    def to_csv(self, path: str | Path) -> Path:
        path = Path(path)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            extra_channels = sorted({key for site in self.sites for key in (site.channel_targets or {})})
            writer.writerow(
                [
                    "x_um",
                    "y_um",
                    "shape",
                    "r_um",
                    "width_um",
                    "length_um",
                    "height_um",
                    "rotation_rad",
                    "rotation_deg",
                    "target_phase_rad",
                    "phase_rad",
                    "phase_error_rad",
                    "transmission",
                    "loss",
                ]
                + [f"target_phase_{name}" for name in extra_channels]
                + [f"phase_error_{name}" for name in extra_channels]
            )
            for site in self.sites:
                rotation = site.candidate.rotation
                targets = site.channel_targets or {}
                errors = site.channel_errors or {}
                writer.writerow(
                    [
                        site.x,
                        site.y,
                        site.candidate.shape,
                        site.candidate.radius,
                        "" if site.candidate.width is None else site.candidate.width,
                        "" if site.candidate.length is None else site.candidate.length,
                        "" if site.candidate.height is None else site.candidate.height,
                        "" if rotation is None else rotation,
                        "" if rotation is None else math.degrees(rotation),
                        site.target_phase,
                        site.candidate.phase,
                        wrap_phase(site.candidate.phase - site.target_phase),
                        site.candidate.transmission,
                        site.loss,
                    ]
                    + [targets.get(name, "") for name in extra_channels]
                    + [errors.get(name, "") for name in extra_channels]
                )
        return path


class PhaseGridDesigner:
    def __init__(
        self,
        library: str | Path | PillarLibrary,
        phase: str | PhaseCallable = "hyperbolic",
        loss: str | LossCallable = "phase_transmission",
        aperture_radius: float = 4.0,
        pitch: float = 0.35,
        shape: str = "circle",
        wavelength: float | None = None,
        focal_length: float | None = None,
        phase_params: dict[str, float] | None = None,
        channels: list[dict[str, Any] | Channel] | None = None,
        phase_mode: str = "dynamic",
        use_pb: bool | None = None,
        rotation_steps: int = 180,
        pb_spin: int = 1,
        loss_params: dict[str, float] | None = None,
        out_dir: str | Path = "phasegrid_design",
        plot_structure: bool = True,
        plot_phase: bool = True,
        plot_propagation: bool = True,
        propagation_z: float | None = None,
        propagation_size: int = 72,
        run_fdtd: bool = False,
        fdtd_runner: Callable[[DesignResult, Path, dict[str, Any]], dict[str, Any] | None] | None = None,
        fdtd_config: dict[str, Any] | None = None,
        backend: str = "auto",
    ):
        self.library = library if isinstance(library, PillarLibrary) else PillarLibrary.from_csv(library)
        self.phase = phase
        self.loss = loss
        self.aperture_radius = aperture_radius
        self.pitch = pitch
        self.shape = shape
        self.phase_params = dict(phase_params or {})
        if wavelength is not None:
            self.phase_params.setdefault("wavelength", wavelength)
        if focal_length is not None:
            self.phase_params.setdefault("focal_length", focal_length)
        self.loss_params = {"phase_weight": 1.0, "transmission_weight": 0.2}
        self.loss_params.update(loss_params or {})
        self.channels = normalize_channels(channels, self.phase, self.phase_params)
        self.use_pb = use_pb
        self.phase_mode = resolve_phase_mode(phase_mode, use_pb)
        self.rotation_steps = rotation_steps
        self.pb_spin = pb_spin
        self.out_dir = Path(out_dir)
        self.should_plot_structure = plot_structure
        self.should_plot_phase = plot_phase
        self.should_plot_propagation = plot_propagation
        self.propagation_z = propagation_z
        self.propagation_size = propagation_size
        self.run_fdtd = run_fdtd
        self.fdtd_runner = fdtd_runner
        self.fdtd_config = dict(fdtd_config or {})
        self.backend = backend

    def run(self, out_dir: str | Path | None = None) -> DesignResult:
        out_dir = Path(out_dir) if out_dir else self.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        coordinates = make_grid(self.aperture_radius, self.pitch, self.shape)

        if self._uses_multichannel_selector():
            sites = self._select_multichannel_sites(coordinates)
        else:
            phase_fn = resolve_phase(self.phase)
            targets = [phase_fn(x, y, self.phase_params) % TAU for x, y in coordinates]
            loss_fn = resolve_loss(self.loss)
            sites = self._select_sites(coordinates, targets, loss_fn)
        result = DesignResult(sites=sites, files={}, summary=self._summary(sites))

        layout_path = result.to_csv(out_dir / "layout.csv")
        result.files["layout"] = layout_path
        summary_path = out_dir / "summary.json"
        summary_path.write_text(json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result.files["summary"] = summary_path
        if self.should_plot_structure:
            result.files["structure"] = plot_structure(out_dir / "structure.svg", sites, self.aperture_radius)
        if self.should_plot_phase:
            result.files["phase"] = plot_phase(out_dir / "phase.svg", sites, self.aperture_radius)
        if self.should_plot_propagation:
            z = self.propagation_z or self.phase_params.get("focal_length", self.aperture_radius * 2.0)
            wavelength = self.phase_params.get("wavelength", 1.0)
            result.files["propagation"] = plot_propagation(out_dir / "propagation.svg", sites, self.aperture_radius, wavelength, z, self.propagation_size)
        if self.run_fdtd:
            if self.fdtd_runner is None:
                raise ValueError("run_fdtd=True requires fdtd_runner")
            fdtd_dir = out_dir / "fdtd"
            fdtd_dir.mkdir(parents=True, exist_ok=True)
            fdtd_output = self.fdtd_runner(result, fdtd_dir, dict(self.fdtd_config)) or {}
            result.summary["fdtd_status"] = str(fdtd_output.get("status", "completed"))
            result.files["fdtd_summary"] = write_fdtd_summary(fdtd_dir / "summary.json", fdtd_output)
            summary_path.write_text(json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result

    def _select_sites(
        self,
        coordinates: list[tuple[float, float]],
        targets: list[float],
        loss_fn: LossCallable,
    ) -> list[DesignSite]:
        use_fast = isinstance(self.loss, str) and self.loss.lower() in {"phase_transmission", "balanced", "phase_only", "phase"}
        if use_fast:
            transmission_weight = 0.0 if str(self.loss).lower() in {"phase_only", "phase"} else self.loss_params.get("transmission_weight", 0.2)
            indices = select_indices(targets, self.library, self.loss_params.get("phase_weight", 1.0), transmission_weight, self.backend)
            sites = []
            for (x, y), target, index in zip(coordinates, targets, indices):
                candidate = self.library.candidates[index]
                loss = loss_fn(target, candidate, x, y, self.loss_params)
                sites.append(DesignSite(x, y, target, candidate, loss))
            return sites

        sites = []
        for (x, y), target in zip(coordinates, targets):
            best_candidate = self.library.candidates[0]
            best_loss = float("inf")
            for candidate in self.library.candidates:
                loss = loss_fn(target, candidate, x, y, self.loss_params)
                if loss < best_loss:
                    best_loss = loss
                    best_candidate = candidate
            sites.append(DesignSite(x, y, target, best_candidate, best_loss))
        return sites

    def _summary(self, sites: list[DesignSite]) -> dict[str, float | int | str]:
        if sites and any(site.channel_errors for site in sites):
            error_values = [
                abs(error)
                for site in sites
                for error in (site.channel_errors or {}).values()
            ]
            mean_abs_error = sum(error_values) / len(error_values) if error_values else 0.0
        else:
            mean_abs_error = sum(abs(wrap_phase(site.candidate.phase - site.target_phase)) for site in sites) / len(sites) if sites else 0.0
        mean_transmission = sum(site.candidate.transmission for site in sites) / len(sites) if sites else 0.0
        return {
            "sites": len(sites),
            "aperture_radius_um": self.aperture_radius,
            "pitch_um": self.pitch,
            "shape": self.shape,
            "phase": self.phase if isinstance(self.phase, str) else "custom",
            "loss": self.loss if isinstance(self.loss, str) else "custom",
            "phase_mode": self.phase_mode,
            "use_pb": bool(self.phase_mode in {"pb", "hybrid"}),
            "channels": len(self.channels),
            "mean_abs_phase_error_rad": mean_abs_error,
            "mean_transmission": mean_transmission,
            "backend": self.backend,
        }

    def _uses_multichannel_selector(self) -> bool:
        return len(self.channels) > 1 or self.phase_mode in {"pb", "hybrid"} or str(self.loss).lower() in {"dualband", "multiband", "pb", "pb_phase", "pb_dualband", "pb_multiband"}

    def _select_multichannel_sites(self, coordinates: list[tuple[float, float]]) -> list[DesignSite]:
        channel_phase_fns = [(channel, resolve_phase(channel.phase)) for channel in self.channels]
        rotations = rotation_grid(self.rotation_steps) if self.phase_mode in {"pb", "hybrid"} else [None]
        sites: list[DesignSite] = []
        for x, y in coordinates:
            targets = {
                channel.name: phase_fn(x, y, dict(channel.phase_params or {})) % TAU
                for channel, phase_fn in channel_phase_fns
            }
            best_candidate = self.library.candidates[0]
            best_loss = float("inf")
            best_errors: dict[str, float] = {}
            for candidate in self.library.candidates:
                for rotation in rotations:
                    loss, errors = self._candidate_multichannel_loss(targets, candidate, rotation)
                    if loss < best_loss:
                        best_loss = loss
                        best_candidate = candidate.with_rotation(rotation)
                        best_errors = errors
            default_target = targets[self.channels[0].name]
            sites.append(
                DesignSite(
                    x=x,
                    y=y,
                    target_phase=default_target,
                    candidate=best_candidate,
                    loss=best_loss,
                    channel_targets=targets,
                    channel_errors=best_errors,
                )
            )
        return sites

    def _candidate_multichannel_loss(
        self,
        targets: dict[str, float],
        candidate: PillarCandidate,
        rotation: float | None,
    ) -> tuple[float, dict[str, float]]:
        total = 0.0
        errors: dict[str, float] = {}
        phase_weight = self.loss_params.get("phase_weight", 1.0)
        for channel in self.channels:
            dynamic_phase = candidate.phase_for(channel.phase_col)
            pb_phase = 0.0 if rotation is None else 2.0 * channel.pb_spin * self.pb_spin * rotation
            if self.phase_mode == "pb":
                realized = pb_phase
            elif self.phase_mode == "hybrid":
                realized = dynamic_phase + pb_phase
            else:
                realized = dynamic_phase
            error = phase_distance(targets[channel.name], realized)
            transmission = candidate.transmission_for(channel.transmission_col)
            transmission_loss = 1.0 - transmission
            total += channel.weight * phase_weight * error * error
            total += channel.transmission_weight * transmission_loss * transmission_loss
            errors[channel.name] = error
        return total, errors


def make_grid(aperture_radius: float, pitch: float, shape: str) -> list[tuple[float, float]]:
    if aperture_radius <= 0 or pitch <= 0:
        raise ValueError("aperture_radius and pitch must be positive")
    half_steps = int(math.floor(aperture_radius / pitch))
    points = []
    for ix in range(-half_steps, half_steps + 1):
        for iy in range(-half_steps, half_steps + 1):
            x = ix * pitch
            y = iy * pitch
            if shape == "circle" and math.hypot(x, y) > aperture_radius + 1e-12:
                continue
            if shape not in {"circle", "square"}:
                raise ValueError("shape must be 'circle' or 'square'")
            points.append((x, y))
    return points


def write_fdtd_summary(path: Path, output: dict[str, Any]) -> Path:
    path.write_text(json.dumps(output, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def rotation_grid(steps: int) -> list[float]:
    if steps <= 0:
        raise ValueError("rotation_steps must be positive")
    return [index * math.pi / steps for index in range(steps)]


def resolve_phase_mode(phase_mode: str, use_pb: bool | None) -> str:
    if use_pb is None:
        resolved = phase_mode
    else:
        resolved = "hybrid" if use_pb else "dynamic"
    if resolved not in {"dynamic", "pb", "hybrid"}:
        raise ValueError("phase_mode must be 'dynamic', 'pb', or 'hybrid'")
    return resolved
