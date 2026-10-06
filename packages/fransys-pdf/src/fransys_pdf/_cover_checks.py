"""`COVER_OVERFLOW` (page-frame spec R11.6): the cover and the revision table may overlap.

The cover text and the revision-history table can be estimated to overlap.

A NEW module, not `checks.py` (P3's own); `checks.py` registers it with one added import and
one added call in its per-document loop (named in the hand-back). `_pages.cover_page` never
moves the table out of the way of an oversized cover (R11.6's "the table keeps its place"),
so this is the only signal an engineer gets that the two would collide.

The estimate is a character-count heuristic, not a Typst compile: this package never compiles
inside a check (`checks.py`'s own findings are all cheap, deterministic reads of the model and
`SheetFormat`, never the `typst` package `test_frame_compiled.py` alone reaches for), so this
stays the same shape -- an approximate wrapped-line count per cover element and per
revision-history row, at the font sizes and content width `_pages.cover_page` actually uses,
against the content box `SheetFormat` gives.
"""

from math import ceil
from typing import TYPE_CHECKING

from fransys_model.derive import revision_history
from fransys_model.kernel import Finding, Severity

from ._geometry import document_heading, document_release, resolve_sheet_format
from ._markdown import BulletList, Heading, NumberedList, Paragraph, Unsupported, parse
from ._pages import DESCRIPTION_WIDTH_MM, TABLE_HEADER_MM

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Document, PageKind, Revision

# R4's inner padding, the same value `_pages._PADDING_MM` and `_frame.py`'s own private
# constant independently apply: the flowed cover text and the table both lose this much of
# the content box's own height on every side (spec-fixed, not tunable).
_PADDING_MM = 5
_HEADING_PT = 16  # `_geometry.preamble`'s `#show heading.where(level: 1)` size
_BODY_PT = 10  # `_geometry.preamble`'s base text size
_TABLE_PT = 9  # `_geometry.preamble`'s `#show table: set text(size: 9pt)`
_CHAR_WIDTH_EM = 0.5  # a crude average glyph width for Liberation Serif, as a fraction of its size
_LINE_HEIGHT_EM = 1.3
_MM_PER_PT = 25.4 / 72.0


def _pt_to_mm(pt: float) -> float:
    return pt * _MM_PER_PT


def _line_count(text: str, *, width_mm: float, size_pt: float) -> int:
    """A crude wrapped-line estimate: `text`'s length against `width_mm` at `size_pt`."""
    if not text:
        return 1
    char_width_mm = _pt_to_mm(size_pt) * _CHAR_WIDTH_EM
    chars_per_line = max(1, int(width_mm / char_width_mm))
    return max(1, ceil(len(text) / chars_per_line))


def _text_height_mm(text: str, *, width_mm: float, size_pt: float) -> float:
    return (
        _line_count(text, width_mm=width_mm, size_pt=size_pt) * _pt_to_mm(size_pt) * _LINE_HEIGHT_EM
    )


def _element_text(element: Heading | Paragraph | Unsupported) -> str:
    if isinstance(element, Unsupported):
        return element.text
    return "".join(run.text for run in element.runs)


def _cover_text_height_mm(model: Model, record: Document, *, width_mm: float) -> float:
    """The cover's estimated flowed height: heading plus every element (`preamble` sizes)."""
    total = _text_height_mm(document_heading(model, record), width_mm=width_mm, size_pt=_HEADING_PT)
    for element in parse(record.cover):
        if isinstance(element, (BulletList, NumberedList)):
            for item in element.items:
                text = "".join(run.text for run in item)
                total += _text_height_mm(text, width_mm=width_mm, size_pt=_BODY_PT)
            continue
        size = _HEADING_PT if isinstance(element, Heading) else _BODY_PT
        total += _text_height_mm(_element_text(element), width_mm=width_mm, size_pt=size)
    return total


def _table_height_mm(entries: tuple[Revision, ...]) -> float:
    """The revision table's estimated height (R11.6): header plus rows wrapped at 120 mm."""
    if not entries:
        return 0.0
    rows = sum(
        _text_height_mm(entry.text, width_mm=DESCRIPTION_WIDTH_MM, size_pt=_TABLE_PT)
        for entry in entries
    )
    return TABLE_HEADER_MM + rows


def cover_overflow_findings(
    model: Model, subject: Id[Document], record: Document, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    """`COVER_OVERFLOW` (`WARNING`): cover plus revision table exceed the box (R11.6)."""
    sheet = resolve_sheet_format(model, record, pages)
    width_mm = sheet.content_width_mm - 2 * _PADDING_MM
    text_height = _cover_text_height_mm(model, record, width_mm=width_mm)
    entries = revision_history(model, document_release(model, record))
    table_height = _table_height_mm(entries)
    available = sheet.content_height_mm - 2 * _PADDING_MM
    if text_height + table_height <= available:
        return ()
    return (
        Finding(
            code="COVER_OVERFLOW",
            severity=Severity.WARNING,
            subjects=(subject,),
            message=(
                f"cover text ~{text_height:.0f}mm plus the revision table ~{table_height:.0f}mm "
                f"exceeds the {available:.0f}mm content box"
            ),
        ),
    )
