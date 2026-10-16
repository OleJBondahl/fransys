"""Fransys output: document assembly to Typst source (6 and 9)."""

from fransys_model.derive import (
    PRESET_PAGES,
    document_page_kinds,
    page_kinds,
    requests_harness_pages,
)

from ._cover_measure import cover_overflow_finding
from .checks import check
from .codes import FINDING_CODES
from .document import source
from .fonts import font_dir

document_pages = document_page_kinds

__all__ = [
    "FINDING_CODES",
    "PRESET_PAGES",
    "check",
    "cover_overflow_finding",
    "document_pages",
    "font_dir",
    "page_kinds",
    "requests_harness_pages",
    "source",
]
