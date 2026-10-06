"""Drawing pages, shared by `document.py` and `checks.py` so they agree on "no drawings" (P11)."""

from collections import Counter
from typing import TYPE_CHECKING

from fransys_model.derive import (
    cable_title,
    cell_text,
    column_values,
    document_unit,
    external,
    harness_cables,
    item_designation,
    top_level_cables,
    unit_cables,
)
from fransys_model.derive.drawing_text import external_note, page_title, page_title_groups
from fransys_model.kernel import render_id
from fransys_model.vocab import DocumentPreset, PageKind, aspect_nodes

from ._frame import TitleBlockFields, background, text_margin
from ._geometry import (
    _drawing_set_pages,
    document_facts,
    location_label,
    project_notice,
    subject_label,
    undrawn_replica_only_sets,
)
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import HarnessCable
    from fransys_model.kernel import Model
    from fransys_model.layout import DrawingSet, Page, SheetFormat
    from fransys_model.vocab import Document

NO_DRAWINGS = '#par(text("No drawings."))'


def _page_title_labels(model: Model, page: Page) -> str:
    """The page's `=` group labels, `page_title`'s fallback, same filter (R11.7, model-0097)."""
    nodes = aspect_nodes(model)
    return " ".join(f"={nodes[group.group].label}" for group in page_title_groups(model, page))


def schematic_pages(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[Page, ...]:
    """The subject's drawing-set pages (P7, U3); empty for an item subject (no `pcb_review` yet)."""
    if record.location is None and record.unit is None and record.unit_name is None:
        return ()
    return _drawing_set_pages(model, record, pages)


def replica_only_sets(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[DrawingSet, ...]:
    """The matched sets skipped as replica-only; empty without a location or unit subject."""
    if record.location is None and record.unit is None and record.unit_name is None:
        return ()
    return undrawn_replica_only_sets(model, record, pages)


def schematic_missing_keys(
    pages_found: tuple[Page, ...], svgs: Mapping[str, str]
) -> tuple[str, ...]:
    """The `render_id`s of `pages_found` that `svgs` has no entry for (spec P7, P11)."""
    return tuple(render_id(page.id) for page in pages_found if render_id(page.id) not in svgs)


def schematic_source(
    model: Model,
    record: Document,
    sheet: SheetFormat,
    pages_found: tuple[Page, ...],
    svgs: Mapping[str, str],
) -> str:
    """The SCHEMATIC section: full-bleed pages (R1-R4), `n / N` counted per drawing set (R3, U3)."""
    if not pages_found or schematic_missing_keys(pages_found, svgs):
        fields = TitleBlockFields(
            *document_facts(model, record),
            page_title="Schematic",
            scope=subject_label(model, record),
            sheet_counter="",
            notice=project_notice(model),
            logo=record.logo,
        )
        margin = text_margin(sheet)
        return f"#page(margin: {margin}, background: {background(sheet, fields)})[{NO_DRAWINGS}]"
    assert (  # noqa: S101 -- `pages_found` is non-empty only when one of these three is
        record.location is not None or record.unit is not None or record.unit_name is not None
    )
    scope = (
        location_label(model, record.location)
        if record.location is not None
        else subject_label(model, record)
    )
    totals = Counter(page.drawing_set for page in pages_found)
    blocks = []
    for page in pages_found:
        fields = TitleBlockFields(
            *document_facts(model, record),
            page_title=page_title(model, page),
            scope=scope,
            sheet_counter=f"{page.number} / {totals[page.drawing_set]}",
            notice=project_notice(model),
            logo=record.logo,
            page_title_fallback=_page_title_labels(model, page),
        )
        image = f'#image(bytes({literal(svgs[render_id(page.id)])}), format: "svg")'
        blocks.append(f"#page(margin: 0mm, background: {background(sheet, fields)})[{image}]")
    return "\n#pagebreak()\n".join(blocks)


def requests_harness_pages(pages: tuple[PageKind, ...]) -> bool:
    """Whether `pages` holds `CONTENTS` or `HARNESS_DRAWING`, the page kinds that show cables.

    The one home of this test (decision pdf-0015): `harness_cables_for` reads it, since the
    `CONTENTS` table prints the cables' rows and `HARNESS_DRAWING` draws them.
    """
    return PageKind.CONTENTS in pages or PageKind.HARNESS_DRAWING in pages


def harness_cables_for(
    model: Model, record: Document, pages: tuple[PageKind, ...]
) -> tuple[HarnessCable, ...]:
    """The subject's cables: SYSTEM all top-level, a unit its own only (P8, U3, pdf-0015)."""
    if not requests_harness_pages(pages):
        return ()
    if record.preset is DocumentPreset.SYSTEM:
        return top_level_cables(model)
    if (unit := document_unit(model, record)) is not None:
        return unit_cables(model, unit)
    if record.item is None:
        return ()
    return harness_cables(model, record.item)


def system_has_no_top_level_cables(
    record: Document, cables_found: tuple[HarnessCable, ...]
) -> bool:
    """A SYSTEM document whose model has no top-level cable at all (units spec U3)."""
    return record.preset is DocumentPreset.SYSTEM and not cables_found


_CORE_HEADERS = ("Core", "From", "To", "Label")
_CORE_COLUMNS = ("index", "end_a_designation", "end_b_designation", "label")


def _cable_heading_line(cable: HarnessCable) -> str:
    """CT3's heading: designation, mpn, description, cores x gauge, length; unset ones omitted."""
    parts = [cable.designation]
    if cable.mpn:
        parts.append(cable.mpn)
    if cable.description:
        parts.append(cable.description)
    if cable.core_count is not None and cable.gauge_mm2 is not None:
        parts.append(f"{cable.core_count} x {cable.gauge_mm2} mm²")
    if cable.length_mm is not None:
        parts.append(f"{cable.length_mm} mm")
    return ", ".join(parts)


def _cable_external_note(model: Model, record: Document, cable: HarnessCable) -> str | None:
    """CT3's "by others" line (Y3), SYSTEM only: external cable and ends, not blank ends."""
    if record.preset is not DocumentPreset.SYSTEM:
        return None
    covered = [cable.designation] if external(model, cable.cable) else []
    covered.extend(
        end.designation for end in cable.ends if end.designation and external(model, end.item)
    )
    if not covered:
        return None
    return f"{external_note()}: {', '.join(covered)}"


def _cable_table(cable: HarnessCable) -> str:
    """CT3's per-core table, shared `cell_text` (pdf-0016); header only without cores (CT4)."""
    header = "table.header(" + ", ".join(f"strong(text({literal(h)}))" for h in _CORE_HEADERS) + ")"
    cells = [header]
    for core in cable.cores:
        values = column_values(core, _CORE_COLUMNS)
        cells.extend(f"text({literal(cell_text(value))})" for value in values)
    return f"#table(columns: {len(_CORE_HEADERS)}, stroke: 0.5pt, " + ", ".join(cells) + ")"


def _cable_page(model: Model, record: Document, sheet: SheetFormat, cable: HarnessCable) -> str:
    """One HARNESS_DRAWING table page for `cable` (CT2, CT3, pdf-0018), in `text_margin` (R4)."""
    assert (  # noqa: S101 -- a harness document's subject is an item or a unit, or this is SYSTEM
        record.item is not None
        or record.unit is not None
        or record.unit_name is not None
        or record.preset is DocumentPreset.SYSTEM
    )
    scope = (
        item_designation(model, record.item)
        if record.item is not None
        else subject_label(model, record)
    )
    fields = TitleBlockFields(
        *document_facts(model, record),
        page_title=cable_title(cable),
        scope=scope,
        sheet_counter="",
        notice=project_notice(model),
        logo=record.logo,
    )
    lines = [f"#strong(text({literal(_cable_heading_line(cable))}))"]
    note = _cable_external_note(model, record, cable)
    if note is not None:
        lines.append(f"#linebreak()#text({literal(note)})")
    lines.append(_cable_table(cable))
    body = "\n".join(lines)
    margin = text_margin(sheet)
    return f"#page(margin: {margin}, background: {background(sheet, fields)})[{body}]"


def harness_drawing_source(
    model: Model, record: Document, sheet: SheetFormat, cables_found: tuple[HarnessCable, ...]
) -> str:
    """One table page per cable (CT2, P8, pdf-0018); `""` for SYSTEM without top-level cables."""
    if system_has_no_top_level_cables(record, cables_found):
        return ""
    if not cables_found:
        fields = TitleBlockFields(
            *document_facts(model, record),
            page_title="Harness drawing",
            scope=subject_label(model, record),
            sheet_counter="",
            notice=project_notice(model),
            logo=record.logo,
        )
        margin = text_margin(sheet)
        return f"#page(margin: {margin}, background: {background(sheet, fields)})[{NO_DRAWINGS}]"
    return "\n#pagebreak()\n".join(
        _cable_page(model, record, sheet, cable) for cable in cables_found
    )
