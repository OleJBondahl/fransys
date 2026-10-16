"""Page geometry: paper, margins, header, footer, type sizes."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    PRESET_HEADINGS,
    document_drawing_sets,
    document_facts,
    document_unit,
    is_replica_only_undrawn,
    page_order_key,
    subject_label,
    unit_release,
)
from fransys_model.layout import (
    DrawingSet,
    Page,
    SheetFormat,
    layout_of,
    sheet_format_of,
)
from fransys_model.vocab import PageKind

from ._labels import ROMAN
from ._sizes import Sizes, font_mm
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Document, UnitRelease


def _drawing_set_pages(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[Page, ...]:
    """The subject's drawing-set pages in `number` order, replica-only sets skipped."""
    if PageKind.SCHEMATIC not in pages:
        return ()
    matched = document_drawing_sets(model, record)
    if not matched:
        return ()
    order = {
        drawing_set.id: drawing_set.number
        for drawing_set in matched
        if not is_replica_only_undrawn(model, drawing_set)
    }
    if not order:
        return ()
    on_these_sets = [page for page in layout_of(model, Page).values() if page.drawing_set in order]
    return tuple(
        sorted(on_these_sets, key=lambda page: page_order_key(order[page.drawing_set], page))
    )


def undrawn_replica_only_sets(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[DrawingSet, ...]:
    """The sets `_drawing_set_pages` skips as replica-only; shared so the two cannot disagree."""
    if PageKind.SCHEMATIC not in pages:
        return ()
    return tuple(
        drawing_set
        for drawing_set in document_drawing_sets(model, record)
        if is_replica_only_undrawn(model, drawing_set)
    )


def mixed_sheet_formats(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[tuple[SheetFormat, tuple[Page, ...]], ...]:
    """Each sheet format the pages name, with its pages; empty unless more than one."""
    set_pages = _drawing_set_pages(model, record, pages)
    grouped: dict[Id[SheetFormat] | None, list[Page]] = {}
    for page in set_pages:
        grouped.setdefault(page.sheet_format, []).append(page)
    if len(grouped) <= 1:
        return ()
    return tuple((sheet_format_of(model, key), tuple(group)) for key, group in grouped.items())


def document_metadata(model: Model, record: Document) -> str:
    """`#set document(...)` from `document_facts`; the date is never `auto`."""
    title, _number, _customer, _revision, revision_date, author = document_facts(model, record)
    if not revision_date:
        date = "none"
    else:
        year, month, day = (int(part) for part in revision_date.split("-"))
        date = f"datetime(year: {year}, month: {month}, day: {day})"
    return f"#set document(title: {literal(title)}, author: {literal(author)}, date: {date})"


def document_release(model: Model, record: Document) -> Id[UnitRelease] | None:
    """The release whose revision history `record` shows: its unit's, `None` for the project's."""
    unit = document_unit(model, record)
    if unit is None:
        return None
    return unit_release(model, unit).id


def document_heading(model: Model, record: Document) -> str:
    """`<preset words> — <subject label>`, the words alone when the label is empty."""
    words = PRESET_HEADINGS[record.preset]
    subject = subject_label(model, record)
    if not subject:
        return words
    return f"{words} — {subject}"


def preamble(sizes: Sizes, sheet: SheetFormat) -> str:
    """Text, page size and type sizes, once; margin and background are per page kind."""
    return "\n".join(
        [
            f'#set text(font: "DejaVu Sans", size: {font_mm(sizes.body)})',
            f"#set page(width: {sheet.width_mm}mm, height: {sheet.height_mm}mm, {ROMAN})",
            f"#show heading.where(level: 1): set text(size: {font_mm(sizes.heading_1)})",
            f"#show heading.where(level: 2): set text(size: {font_mm(sizes.heading_2)})",
            f"#show heading.where(level: 3): set text(size: {font_mm(sizes.body)})",
            f"#show table: set text(size: {font_mm(sizes.label)})",
        ]
    )


PADDING_MM = 5  # non-drawing pages' inner padding inside the content box


def text_margin(sheet: SheetFormat) -> str:
    """A `#set page(margin: ...)`: content box plus 5 mm padding; harness too (pdf-0009)."""
    left = sheet.content_x_mm + PADDING_MM
    top = sheet.content_y_mm + PADDING_MM
    right = (sheet.width_mm - sheet.content_x_mm - sheet.content_width_mm) + PADDING_MM
    bottom = (sheet.height_mm - sheet.content_y_mm - sheet.content_height_mm) + PADDING_MM
    return f"(left: {left}mm, top: {top}mm, right: {right}mm, bottom: {bottom}mm)"
