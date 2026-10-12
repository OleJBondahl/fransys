"""Lint layer: the QA gate, geometric checks and connectivity coherence apart."""

from ._harness import HarnessInk
from .chains import lint_chains, lone_cells
from .codes import ALL_CODES
from .coherence import check_coherence
from .diagram import lint_diagram
from .fill import fill_shares, lint_fill
from .geometric import geometry_by_page, lint_geometry
from .members import check_members, check_nowhere

__all__ = (
    "ALL_CODES",
    "HarnessInk",
    "check_coherence",
    "check_members",
    "check_nowhere",
    "fill_shares",
    "geometry_by_page",
    "lint_chains",
    "lint_diagram",
    "lint_fill",
    "lint_geometry",
    "lone_cells",
)
