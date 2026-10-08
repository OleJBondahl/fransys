"""Drawing pages, shared by `document.py` and `checks.py` so they agree on "no drawings" (P11)."""

from collections import Counter
from typing import TYPE_CHECKING

from fransys_model.derive import (
    document_unit,
    harness_cables,
    item_designation,
    top_level_cables,
    unit_cables,
)
from fransys_model.derive.cable_drawing import (
    cable_block_key,
    cable_subject,
    drawn_blocks,
    wire_harness_subjects,
)
from fransys_model.derive.drawing_text import page_title, page_title_groups
from fransys_model.kernel import render_id
from fransys_model.vocab import DocumentPreset, PageKind, aspect_nodes, items, parts

from ._cable_runs import Block, part_groups, run_page
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
    from fransys_model.kernel import Id, Model
    from fransys_model.layout import DrawingSet, Page, SheetFormat
    from fransys_model.vocab import Document, Item

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


def _part_line(cable: HarnessCable) -> str:
    """The page's part line (pdf-0021): mpn, description, cores x gauge; unset ones omitted."""
    composite = None
    if cable.core_count is not None and cable.gauge_mm2 is not None:
        composite = f"{cable.core_count} x {cable.gauge_mm2} mm²"
    return _join_part_line(cable.mpn, cable.description, composite)


def _join_part_line(*texts: str | None) -> str:
    """The one part-line format, the lone cable's and the harness's: set texts, comma-joined."""
    return ", ".join(text for text in texts if text)


def _harness_block(model: Model, subject: Id[Item], key: str) -> Block:
    """A harness block: in the run of the harness's own part, or of none (CD9, Q8)."""
    part_id = items(model)[subject].part
    if part_id is None:
        return Block(key, "", "")
    part = parts(model)[part_id]
    return Block(key, part.mpn, _join_part_line(part.mpn, part.description))


def wire_subjects(
    model: Model, record: Document, cables: tuple[HarnessCable, ...]
) -> tuple[Id[Item], ...]:
    """The harnesses with single wires the document draws, by `block_drawn` (HA-H1 A1, pdf-0024).

    A SYSTEM document has none. A unit document has its unit's; a harness document has its own
    item when it has no cable. The CONTENTS table stays cable-only: no row for a wire.
    """
    if record.preset is DocumentPreset.SYSTEM:
        return ()
    unit = document_unit(model, record)
    if unit is None and (record.item is None or cables):
        return ()
    wired = set(wire_harness_subjects(model))
    return tuple(
        subject
        for block_unit, subject in drawn_blocks(model)
        if block_unit == unit and subject in wired and (unit is not None or subject == record.item)
    )


def cable_blocks(
    model: Model, record: Document, cables: tuple[HarnessCable, ...]
) -> tuple[Block, ...]:
    """The document's blocks, one per `cable_subject`, each at its first cable's place (CD12).

    A document reads absolutely unless it is a unit document, whose reading is its unit. A
    harness with wires gets its one block too (`wire_subjects`), after the cable blocks.
    """
    unit = None if record.preset is DocumentPreset.SYSTEM else document_unit(model, record)
    blocks: dict[str, Block] = {}
    for cable in cables:
        subject = cable_subject(model, cable.cable)
        key = cable_block_key(unit, subject)
        if key in blocks:
            continue
        blocks[key] = (
            Block(key, cable.mpn or "", _part_line(cable))
            if subject == cable.cable
            else _harness_block(model, subject, key)
        )
    for wired in wire_subjects(model, record, cables):
        key = cable_block_key(unit, wired)
        blocks.setdefault(key, _harness_block(model, wired, key))
    return tuple(blocks.values())


def run_headings(model: Model, record: Document, cables: tuple[HarnessCable, ...]) -> list[str]:
    """The part heading of each run, in page order: the title-block `page_title` of its pages."""
    return [heading for heading, _ in part_groups(cable_blocks(model, record, cables))]


def block_missing_keys(blocks: tuple[Block, ...], svgs: Mapping[str, str]) -> tuple[str, ...]:
    """The keys of `blocks` that `svgs` has no entry for, as `schematic_missing_keys` does."""
    return tuple(block.key for block in blocks if block.key not in svgs)


def _cable_runs(
    model: Model,
    record: Document,
    sheet: SheetFormat,
    blocks: tuple[Block, ...],
    svgs: Mapping[str, str],
) -> str:
    """One page run per part (pdf-0020); each run's title block names the part number.

    A block with no SVG is left out: `check` reports it, and only intermediates show the page.
    """
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
    runs = []
    for index, (heading, group) in enumerate(part_groups(blocks)):
        fields = TitleBlockFields(
            *document_facts(model, record),
            page_title=heading,
            scope=scope,
            sheet_counter="",
            notice=project_notice(model),
            logo=record.logo,
        )
        bodies = [
            f'#image(bytes({literal(svgs[block.key])}), format: "svg")'
            for block in group
            if block.key in svgs
        ]
        line = group[0].line if group[0].mpn else heading
        runs.append(run_page(sheet, index, line, background(sheet, fields), bodies))
    return "\n#pagebreak()\n".join(runs)


def harness_drawing_source(
    model: Model,
    record: Document,
    sheet: SheetFormat,
    cables_found: tuple[HarnessCable, ...],
    svgs: Mapping[str, str],
) -> str:
    """Cable block pages, one run per part (pdf-0020, pdf-0022); `""` for SYSTEM with no cable."""
    if system_has_no_top_level_cables(record, cables_found):
        return ""
    blocks = cable_blocks(model, record, cables_found)
    if not blocks:
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
    return _cable_runs(model, record, sheet, blocks, svgs)
