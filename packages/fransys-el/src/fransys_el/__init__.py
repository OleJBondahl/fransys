"""Fransys electrical conventions: the values the general layout core takes as options."""

from .placement_kit import Pick, ProblemError, SymbolKit
from .placement_options import Conventions, options
from .placement_problem import build
from .placement_skips import Skipped
from .ref_tints import REF_TINTS
from .texts import OPTIONS, TEXT_ROW_IDS, TEXTS

__all__ = [
    "OPTIONS",
    "REF_TINTS",
    "TEXTS",
    "TEXT_ROW_IDS",
    "Conventions",
    "Pick",
    "ProblemError",
    "Skipped",
    "SymbolKit",
    "build",
    "options",
]
