"""Phase-radius fitting and parameter sweep helpers for metalens design."""

from .designer import DesignResult, DesignSite, PhaseGridDesigner
from .fit import PhaseFit, PhaseSample
from .library import PillarCandidate, PillarLibrary
from .layout import LensLayout, LensPoint
from .search import PhaseGridSearch, SearchResult, SearchRun
from .sweep import Job, Sweep

__version__ = "0.1.0"

__all__ = [
    "DesignResult",
    "DesignSite",
    "Job",
    "LensLayout",
    "LensPoint",
    "PhaseGridDesigner",
    "PhaseGridSearch",
    "PhaseFit",
    "PhaseSample",
    "PillarCandidate",
    "PillarLibrary",
    "SearchResult",
    "SearchRun",
    "Sweep",
    "__version__",
]
