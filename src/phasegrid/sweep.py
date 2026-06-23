from __future__ import annotations

import csv
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Job:
    index: int
    params: dict[str, float | int | str | bool]

    @property
    def name(self) -> str:
        return f"job_{self.index:04d}"

    def write(self, root: str | Path) -> Path:
        job_dir = Path(root) / self.name
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / "params.json"
        path.write_text(json.dumps(self.params, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path


class Sweep:
    def __init__(self, **parameters: Iterable[float | int | str | bool]):
        if not parameters:
            raise ValueError("Sweep needs at least one parameter")
        self.parameters = {key: list(values) for key, values in parameters.items()}
        for key, values in self.parameters.items():
            if not values:
                raise ValueError(f"Sweep parameter {key!r} has no values")

    def jobs(self) -> list[Job]:
        keys = list(self.parameters)
        jobs = []
        for index, values in enumerate(itertools.product(*(self.parameters[key] for key in keys))):
            jobs.append(Job(index=index, params=dict(zip(keys, values))))
        return jobs

    def write(self, root: str | Path) -> list[Job]:
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        jobs = self.jobs()
        for job in jobs:
            job.write(root)
        with (root / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            keys = list(self.parameters)
            writer.writerow(["job"] + keys)
            for job in jobs:
                writer.writerow([job.name] + [job.params[key] for key in keys])
        return jobs


def parse_values(spec: str) -> list[float | str]:
    if ":" in spec:
        start_s, stop_s, step_s = spec.split(":")
        start, stop, step = float(start_s), float(stop_s), float(step_s)
        if step == 0:
            raise ValueError("range step cannot be zero")
        values = []
        value = start
        compare = (lambda x: x <= stop + 1e-12) if step > 0 else (lambda x: x >= stop - 1e-12)
        while compare(value):
            values.append(round(value, 12))
            value += step
        return values
    values = []
    for part in spec.split(","):
        stripped = part.strip()
        try:
            values.append(float(stripped))
        except ValueError:
            values.append(stripped)
    return values

