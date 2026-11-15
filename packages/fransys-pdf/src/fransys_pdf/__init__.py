"""Fransys output: document assembly to Typst source (6 and 9)."""

from .checks import check
from .codes import FINDING_CODES
from .document import source
from .errors import PdfError

__all__ = [
    "FINDING_CODES",
    "PdfError",
    "check",
    "source",
]
