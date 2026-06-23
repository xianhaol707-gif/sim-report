from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Parameter:
    source: str
    name: str
    value: str


@dataclass(frozen=True)
class MetricPoint:
    source: str
    series: str
    x: float
    y: float


@dataclass(frozen=True)
class DatasetSummary:
    source: str
    dataset: str
    shape: str
    dtype: str
    minimum: str = ""
    maximum: str = ""
    mean: str = ""


@dataclass(frozen=True)
class LogFinding:
    source: str
    level: str
    line_number: int
    message: str


@dataclass(frozen=True)
class Inventory:
    parameters: list[Path] = field(default_factory=list)
    tables: list[Path] = field(default_factory=list)
    figures: list[Path] = field(default_factory=list)
    hdf5: list[Path] = field(default_factory=list)
    logs: list[Path] = field(default_factory=list)
    scripts: list[Path] = field(default_factory=list)
    other: list[Path] = field(default_factory=list)

