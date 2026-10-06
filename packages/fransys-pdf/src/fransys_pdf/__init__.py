"""Fransys output: document assembly to Typst source (spec sections 4, 6 and 9)."""

from ._drawings import requests_harness_pages
from .checks import check
from .document import document_pages, source
from .fonts import font_dir
from .presets import PRESET_PAGES, page_kinds

__all__ = [
    "PRESET_PAGES",
    "check",
    "document_pages",
    "font_dir",
    "page_kinds",
    "requests_harness_pages",
    "source",
]
