"""Page geometry: paper, margins, header, footer, type sizes (spec P4, P5, P10)."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    current_revision,
    document_unit,
    drawing_set_is_replica_only,
    item_description,
    item_designation,
    revision_text,
    unit_release,
)
from fransys_model.derive.drawing_text import unit_label
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    Route,
    SheetFormat,
    SymbolPlacement,
    layout_of,
    sheet_format_of,
)
from fransys_model.vocab import DocumentPreset, PageKind, aspect_nodes, projects

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


def _matched_drawing_sets(model: Model, record: Document) -> tuple[DrawingSet, ...]:
    """`record`'s drawing sets by `number`: a location's top-level set, a unit's sets (U1, U3)."""
    all_sets = layout_of(model, DrawingSet).values()
    if record.location is not None:
        matching = [
            drawing_set
            for drawing_set in all_sets
            if drawing_set.location == record.location and drawing_set.unit is None
        ]
    elif (unit := document_unit(model, record)) is not None:
        matching = [drawing_set for drawing_set in all_sets if drawing_set.unit == unit]
    else:
        matching = []
    return tuple(sorted(matching, key=lambda found: found.number))


def _is_replica_only_undrawn(model: Model, drawing_set: DrawingSet) -> bool:
    """Whether the set has placements, all replicas, and no conductor route or `LinkMarker`."""
    pages = {
        page.id for page in layout_of(model, Page).values() if page.drawing_set == drawing_set.id
    }
    has_placement = any(
        placement.page in pages for placement in layout_of(model, SymbolPlacement).values()
    )
    if not has_placement:
        return False
    if not drawing_set_is_replica_only(model, drawing_set.id):
        return False
    has_conductor_route = any(
        route.conductor is not None
        for route in layout_of(model, Route).values()
        if route.page in pages
    )
    has_marker = any(marker.page in pages for marker in layout_of(model, LinkMarker).values())
    return not (has_conductor_route or has_marker)


def _drawing_set_pages(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[Page, ...]:
    """The subject's drawing-set pages in `number` order, replica-only sets skipped (P4, P7)."""
    if PageKind.SCHEMATIC not in pages:
        return ()
    matched = _matched_drawing_sets(model, record)
    if not matched:
        return ()
    order = {
        drawing_set.id: drawing_set.number
        for drawing_set in matched
        if not _is_replica_only_undrawn(model, drawing_set)
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
        for drawing_set in _matched_drawing_sets(model, record)
        if _is_replica_only_undrawn(model, drawing_set)
    )


def resolve_sheet_format(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> SheetFormat:
    """The paper of every page: the first drawing-set page's format, else the house sheet (P4)."""
    set_pages = _drawing_set_pages(model, record, pages)
    return sheet_format_of(model, set_pages[0].sheet_format if set_pages else None)


def mixed_sheet_formats(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[tuple[SheetFormat, tuple[Page, ...]], ...]:
    """Each sheet format the pages name, with its pages; empty unless more than one (P4)."""
    set_pages = _drawing_set_pages(model, record, pages)
    grouped: dict[Id[SheetFormat] | None, list[Page]] = {}
    for page in set_pages:
        grouped.setdefault(page.sheet_format, []).append(page)
    if len(grouped) <= 1:
        return ()
    return tuple((sheet_format_of(model, key), tuple(group)) for key, group in grouped.items())


def document_metadata(model: Model, record: Document) -> str:
    """`#set document(...)` from `document_facts`; the date is never `auto` (P3, UNIT-ID I2)."""
    title, _number, _customer, _revision, revision_date, author = document_facts(model, record)
    if not revision_date:
        date = "none"
    else:
        year, month, day = (int(part) for part in revision_date.split("-"))
        date = f"datetime(year: {year}, month: {month}, day: {day})"
    return f"#set document(title: {literal(title)}, author: {literal(author)}, date: {date})"


def project_facts(model: Model) -> tuple[str, str, str, str, str, str]:
    """(title, number, customer, revision, revision_date, author); all empty with no `Project`."""
    table = projects(model)
    if not table:
        return ("", "", "", "", "", "")
    record = next(iter(table.values()))
    current = current_revision(model)
    return (
        record.title,
        record.number,
        record.customer,
        revision_text(record.version, record.revision),
        "" if current is None else current.date,
        record.author,
    )


def project_notice(model: Model) -> str:
    """The project-wide IP-notice text (spec page-frame R11.4), `""` with no `Project`."""
    table = projects(model)
    if not table:
        return ""
    return next(iter(table.values())).notice


def document_release(model: Model, record: Document) -> Id[UnitRelease] | None:
    """The release whose revision history `record` shows: its unit's, `None` for the project's."""
    unit = document_unit(model, record)
    if unit is None:
        return None
    return unit_release(model, unit).id


def document_facts(model: Model, record: Document) -> tuple[str, str, str, str, str, str]:
    """`project_facts`, or for a unit document the unit release's own, customer empty (U3, I2)."""
    unit = document_unit(model, record)
    if unit is None:
        return project_facts(model)
    _title, _number, _customer, _revision, _revision_date, author = project_facts(model)
    release = unit_release(model, unit)
    matching = current_revision(model, release.id)
    revision_date = "" if matching is None else matching.date
    return (
        release.title,
        release.number,
        "",
        revision_text(release.version, release.revision),
        revision_date,
        author,
    )


def subject_label(model: Model, record: Document) -> str:
    """The heading's subject: location, unit or item label (P5, U3, model-0066); "" for SYSTEM."""
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
    """`<preset words> — <subject label>`, the words alone when the label is empty (P5, U3)."""
    words = _PRESET_WORDS[record.preset]
    subject = subject_label(model, record)
    if not subject:
        return words
    return f"{words} — {subject}"


def preamble(sheet: SheetFormat) -> str:
    """Text, page size and type sizes, once; margin and background are per page kind (P4, R4)."""
    return "\n".join(
        [
            '#set text(font: "Liberation Serif", size: 10pt)',
            f"#set page(width: {sheet.width_mm}mm, height: {sheet.height_mm}mm)",
            "#show heading.where(level: 1): set text(size: 16pt)",
            "#show heading.where(level: 2): set text(size: 13pt)",
            "#show heading.where(level: 3): set text(size: 11pt)",
            "#show table: set text(size: 9pt)",
        ]
    )
