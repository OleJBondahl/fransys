"""`COVER_OVERFLOW`: the cover and the revision table may overlap.

The cover text and the revision-history table can be estimated to overlap.

A NEW module, not `checks.py`; `checks.py` registers it with one added import and
one added call in its per-document loop (named in the hand-back). `_pages.cover_page` never
moves the table out of the way of an oversized cover ("the table keeps its place"),
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

from ._frame import text_width_mm
from ._geometry import document_heading, document_release, resolve_sheet_format
from ._markdown import BulletList, Heading, NumberedList, Paragraph, Unsupported, parse
from ._pages import DESCRIPTION_WIDTH_MM, TABLE_INSET_MM
from ._sizes import sizes_of

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Document, PageKind, Revision

# The inner padding, the same value `_frame.py`'s own private constant applies independently:
# the flowed cover text and the table both lose this much of
# the content box's own height on every side (spec-fixed, not tunable).
_PADDING_MM = 5
_LINE_HEIGHT_EM = 1.3


def _line_count(text: str, *, width_mm: float, size_mm: float) -> int:
    """A wrapped-line estimate: `text`'s measured width against `width_mm` at `size_mm`."""
    return max(1, ceil(text_width_mm(text, size_mm=size_mm) / width_mm))


def _text_height_mm(text: str, *, width_mm: float, size_mm: float) -> float:
    return _line_count(text, width_mm=width_mm, size_mm=size_mm) * size_mm * _LINE_HEIGHT_EM


def _element_text(element: Heading | Paragraph | Unsupported) -> str:
    if isinstance(element, Unsupported):
        return element.text
    return "".join(run.text for run in element.runs)


def _cover_text_height_mm(model: Model, record: Document, *, width_mm: float) -> float:
    """The cover's estimated flowed height: heading plus every element (`preamble` sizes)."""
    sizes = sizes_of(model, record)
    total = _text_height_mm(
        document_heading(model, record), width_mm=width_mm, size_mm=sizes.heading_1
    )
    for element in parse(record.cover):
        if isinstance(element, (BulletList, NumberedList)):
            for item in element.items:
                text = "".join(run.text for run in item)
                total += _text_height_mm(text, width_mm=width_mm, size_mm=sizes.body)
            continue
        size = sizes.heading_1 if isinstance(element, Heading) else sizes.body
        total += _text_height_mm(_element_text(element), width_mm=width_mm, size_mm=size)
    return total


def _table_height_mm(entries: tuple[Revision, ...], label_mm: float) -> float:
    """The revision table's estimated height: header plus rows wrapped at 120 mm."""
    if not entries:
        return 0.0
    rows = sum(
        _text_height_mm(entry.text, width_mm=DESCRIPTION_WIDTH_MM, size_mm=label_mm)
        for entry in entries
    )
    return label_mm + TABLE_INSET_MM + rows


def cover_overflow_findings(
    model: Model, subject: Id[Document], record: Document, pages: tuple[PageKind, ...]
) -> tuple[Finding, ...]:
    """`COVER_OVERFLOW` (`WARNING`): cover plus revision table exceed the box."""
    sheet = resolve_sheet_format(model, record, pages)
    width_mm = sheet.content_width_mm - 2 * _PADDING_MM
    text_height = _cover_text_height_mm(model, record, width_mm=width_mm)
    entries = revision_history(model, document_release(model, record))
    table_height = _table_height_mm(entries, sizes_of(model, record).label)
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
