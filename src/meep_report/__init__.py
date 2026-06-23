"""Report generator for Meep/FDTD simulation folders."""

from .report import ReportOptions, ReportResult, build_report

__version__ = "0.2.0"

__all__ = ["ReportOptions", "ReportResult", "__version__", "build_report"]
