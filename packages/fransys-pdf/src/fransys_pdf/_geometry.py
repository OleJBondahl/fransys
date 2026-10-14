"""Page geometry: paper, margins, header, footer, type sizes."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    document_drawing_sets,
    document_facts,
    document_unit,
    is_replica_only_undrawn,
    item_description,
    item_designation,
    unit_release,
)
from fransys_model.derive.drawing_text import unit_label
from fransys_model.layout import (
    DrawingSet,
    Page,
    SheetFormat,
    layout_of,
    sheet_format_of,
)
from fransys_model.vocab import DocumentPreset, PageKind, aspect_nodes

from ._labels import ROMAN
from ._sizes import Sizes, font_mm
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Document, UnitRelease

_PRESET_WORDS: dict[DocumentPreset, str] = {
    DocumentPreset.CABINET_SCHEMATIC: "Cabinet schematic",
    DocumentPreset.HARNESS_DRAWING: "Harness drawing",
    DocumentPreset.PCB_SCHEMATIC: "PCB schematic",
    DocumentPreset.SYSTEM: "System",
}


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
    return tuple(sorted(on_these_sets, key=lambda page: (order[page.drawing_set], page.number)))


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


def resolve_sheet_format(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> SheetFormat:
    """The paper of every page: the first drawing-set page's format, else the house sheet."""
    set_pages = _drawing_set_pages(model, record, pages)
    return sheet_format_of(model, set_pages[0].sheet_format if set_pages else None)


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


def subject_label(model: Model, record: Document) -> str:
    """The heading's subject: location, unit or item label (model-0066); "" for SYSTEM."""
    if record.location is not None:
        node = aspect_nodes(model)[record.location]
        return f"{node.label} {node.description}"
    unit = document_unit(model, record)
    if unit is not None:
        return unit_label(model, unit)
    if record.preset is DocumentPreset.SYSTEM:
        return ""
    item_id = record.item
    assert item_id is not None  # noqa: S101 -- Document.__post_init__ requires one of the three, or SYSTEM
    return f"{item_designation(model, item_id)} {item_description(model, item_id)}"


def location_label(model: Model, location: Id[AspectNode]) -> str:
    """`location`'s short code alone (e.g. `C1`), for a drawing page's scope cell."""
    return aspect_nodes(model)[location].label


def document_heading(model: Model, record: Document) -> str:
    """`<preset words> — <subject label>`, the words alone when the label is empty."""
    words = _PRESET_WORDS[record.preset]
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
