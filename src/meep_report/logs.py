from __future__ import annotations

import re
from pathlib import Path

from .models import LogFinding


PATTERNS = [
    ("error", re.compile(r"\b(error|exception|traceback|failed|nan)\b", re.IGNORECASE)),
    ("warning", re.compile(r"\b(warn|warning|deprecated|unstable)\b", re.IGNORECASE)),
    ("done", re.compile(r"\b(done|finished|complete|elapsed|time elapsed)\b", re.IGNORECASE)),
]


def scan_logs(results_dir: Path, log_files: list[Path]) -> list[LogFinding]:
    findings: list[LogFinding] = []
    for path in log_files:
        source = path.relative_to(results_dir).as_posix()
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            for level, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(LogFinding(source, level, index, line.strip()[:240]))
                    break
    return findings[:500]

