"""Measuring helpers for EXACT-SIZES A1, A2 and A4: what a finished PDF really prints.

Test-only (pypdfium2 is a dev dependency). Reads a PDF's bytes; touches no file.
- `capital_boxes`: each H, E or K that pdfium finds, with its capital height in mm measured
  twice: the char box pdfium composes through every matrix, and the dark pixels of a crop of
  the page around the char. The box runs about 1.5 % tall (pdfium pads the glyph box), so the
  tests read the ink; the box stays in the report as the A1 "character box".
- `text_objects`: every text object of every page, its capital height in mm from its font size
  times `CAPITAL_RATIO`, scaled by every matrix down to it (A1, E-amended).
- `stroke_widths`: every stroked path's width in mm, composed through every matrix of its
  form-XObject chain.
- `font_names`: the font each character is set in.
"""

from __future__ import annotations

import ctypes
import math
import re
from collections import Counter
from dataclasses import dataclass

import pypdfium2 as pdfium
from pypdfium2 import raw
from pypdfium2._helpers.pageobjects import PdfObject
from root_library import CAPITAL_RATIO

_MM_PER_PT = 25.4 / 72
_SCALE = 40  # render pixels per pt: one pixel is 0.009 mm
_PAD_PT = 0.8  # vertical margin of the crop around a char box


@dataclass(frozen=True)
class CapBox:
    """One measured capital: its word, page, font and two capital heights (mm)."""

    char: str
    word: str
    page: int
    font: str
    box_mm: float
    ink_mm: float


def _word_at(text: str, index: int) -> str:
    start = index
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    end = index
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[start:end]


def _font_name(textpage: pdfium.PdfTextPage, index: int) -> str:
    buffer = (ctypes.c_char * 256)()
    flags = ctypes.c_int()
    raw.FPDFText_GetFontInfo(textpage, index, buffer, 256, flags)
    return buffer.value.decode("latin-1")


def _ink_height_mm(page: pdfium.PdfPage, box: tuple[float, float, float, float]) -> float:
    left, bottom, right, top = box
    width, height = page.get_size()
    crop = (
        left,
        max(0.0, bottom - _PAD_PT),
        max(0.0, width - right),
        max(0.0, height - top - _PAD_PT),
    )
    bitmap = page.render(scale=_SCALE, crop=crop, grayscale=True)
    rows = [
        y
        for y in range(bitmap.height)
        if any(bitmap.buffer[y * bitmap.stride + x] < 128 for x in range(bitmap.width))
    ]
    assert rows, "no ink inside a char box"
    assert rows[0] > 0, "ink touches the crop top"
    assert rows[-1] < bitmap.height - 1, "ink touches the crop bottom"
    return (rows[-1] - rows[0] + 1) / _SCALE * _MM_PER_PT


def capital_boxes(pdf_bytes: bytes, chars: str = "HEK") -> list[CapBox]:
    """Every char of `chars` in the PDF, measured (A1)."""
    found = []
    for number, page in enumerate(pdfium.PdfDocument(pdf_bytes)):
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        for index in range(textpage.count_chars()):
            char = text[index] if index < len(text) else ""
            if char not in chars:
                continue
            edges = [ctypes.c_double() for _ in range(4)]
            raw.FPDFText_GetCharBox(textpage, index, *edges)
            left, right, bottom, top = (edge.value for edge in edges)
            found.append(
                CapBox(
                    char=char,
                    word=_word_at(text, index),
                    page=number,
                    font=_font_name(textpage, index),
                    box_mm=(top - bottom) * _MM_PER_PT,
                    ink_mm=_ink_height_mm(page, (left, bottom, right, top)),
                )
            )
    return found


def font_names(pdf_bytes: bytes) -> Counter[str]:
    """The font of every non-blank char in the PDF, counted (A4)."""
    names: Counter[str] = Counter()
    for page in pdfium.PdfDocument(pdf_bytes):
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        for index in range(textpage.count_chars()):
            if index < len(text) and not text[index].isspace():
                names[_font_name(textpage, index)] += 1
    return names


def _chain_scale(obj: PdfObject) -> float:
    """The linear scale of an object's matrix times every parent form's matrix."""
    scale = 1.0
    node: object = obj
    while isinstance(node, PdfObject):
        matrix = node.get_matrix()
        scale *= math.sqrt(abs(matrix.a * matrix.d - matrix.b * matrix.c))
        node = node.parent
    return scale


def stroke_widths(pdf_bytes: bytes) -> Counter[float]:
    """Every stroked path's width in mm (to 0.001), through every matrix: width counts (A2)."""
    widths: Counter[float] = Counter()
    for page in pdfium.PdfDocument(pdf_bytes):
        for obj in page.get_objects(max_depth=8):
            if obj.type != raw.FPDF_PAGEOBJ_PATH:
                continue
            width, fill, stroke = ctypes.c_float(), ctypes.c_int(), ctypes.c_int()
            raw.FPDFPath_GetDrawMode(obj.raw, fill, stroke)
            if not stroke.value:
                continue
            raw.FPDFPageObj_GetStrokeWidth(obj.raw, width)
            widths[round(width.value * _chain_scale(obj) * _MM_PER_PT, 3)] += 1
    return widths


@dataclass(frozen=True)
class TextObject:
    """One PDF text object: page, text, capital height (mm), whether a matrix turns it, and its
    bounds (left, bottom, right, top) in mm on a page of `page_mm` (width, height), y up."""

    page: int
    text: str
    cap_mm: float
    turned: bool
    bounds_mm: tuple[float, float, float, float]
    page_mm: tuple[float, float]


def _text_scale(obj: PdfObject) -> tuple[float, bool]:
    """The vertical-axis scale of every matrix down to `obj`, and whether any one turns it.

    A matrix's scale is the length of its vertical column vector, sqrt(c^2 + d^2), so a turned
    text measures like an upright one.
    """
    scale, turned = 1.0, False
    node: object = obj
    while isinstance(node, PdfObject):
        matrix = node.get_matrix()
        scale *= math.hypot(matrix.c, matrix.d)
        turned = turned or abs(matrix.b) > 1e-6 or abs(matrix.c) > 1e-6
        node = node.parent
    return scale, turned


def _object_text(obj: PdfObject, textpage: pdfium.PdfTextPage) -> str:
    wanted = raw.FPDFTextObj_GetText(obj.raw, textpage, None, 0)
    buffer = (ctypes.c_ushort * (wanted // 2 + 1))()
    raw.FPDFTextObj_GetText(obj.raw, textpage, buffer, len(buffer))
    return bytes(buffer).decode("utf-16-le").rstrip("\0")


def text_objects(pdf_bytes: bytes) -> list[TextObject]:
    """Every text object of every page, measured through every matrix (A1)."""
    found = []
    for number, page in enumerate(pdfium.PdfDocument(pdf_bytes)):
        textpage = page.get_textpage()
        width, height = page.get_size()
        for obj in page.get_objects(max_depth=8):
            if obj.type != raw.FPDF_PAGEOBJ_TEXT:
                continue
            size = ctypes.c_float()
            raw.FPDFTextObj_GetFontSize(obj.raw, size)
            scale, turned = _text_scale(obj)
            found.append(
                TextObject(
                    page=number,
                    text=_object_text(obj, textpage),
                    cap_mm=size.value * scale * _MM_PER_PT * float(CAPITAL_RATIO),
                    turned=turned,
                    bounds_mm=tuple(edge * _MM_PER_PT for edge in obj.get_bounds()),
                    page_mm=(width * _MM_PER_PT, height * _MM_PER_PT),
                )
            )
    return found


def has_page_title(text: str, title: str) -> bool:
    """Whether a page's title block shows page title `title`, whitespace ignored.

    pdfium breaks a busy page's drawn title block into one line per character, so the check
    reads the text with no whitespace and needs the block's label run beside the title.
    """
    squeezed = re.sub(r"\s+", "", text)
    return "CustomerAuthor" in squeezed and title.replace(" ", "") in squeezed
