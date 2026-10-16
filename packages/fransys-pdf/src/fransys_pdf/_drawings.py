"""Drawing pages, shared by `document.py` and `checks.py` so they agree on "no drawings"."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    CableBlockRef,
    SheetKey,
    cable_blocks,
    cable_runs,
    schematic_page_ids,
    system_has_no_top_level_cables,
)
from fransys_model.derive import replica_only_sets as matched_replica_only_sets
from fransys_model.derive.page_nav import outline_sheets
from fransys_model.kernel import render_id
from fransys_model.vocab import PageKind

from ._background import page_background
from ._cable_runs import run_page
from ._geometry import text_margin
from ._labels import RESTART, sheet_label
from ._links import page_links
from ._marks import sheet_mark
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import (
        DocumentRow,
        HarnessCable,
        PageId,
        ReplicaOnlySet,
        SheetBackground,
        SheetRow,
    )
    from fransys_model.derive.page_nav import OutlineSheet
    from fransys_model.kernel import Model

NO_DRAWINGS = '#par(text("No drawings."))'


def schematic_pages(
    model: Model, record: DocumentRow, pages: tuple[PageKind, ...]
) -> tuple[PageId, ...]:
    """The subject's drawing-set pages; empty for an item subject (no `pcb_review` yet)."""
    return schematic_page_ids(model, record.id, pages)


def replica_only_sets(
    model: Model, record: DocumentRow, pages: tuple[PageKind, ...]
) -> tuple[ReplicaOnlySet, ...]:
    """The matched sets skipped as replica-only; empty without a location or unit subject."""
    return matched_replica_only_sets(model, record.id, pages)


def schematic_missing_keys(
    pages_found: tuple[PageId, ...], svgs: Mapping[str, str]
) -> tuple[str, ...]:
    """The `render_id`s of `pages_found` that `svgs` has no entry for."""
    return tuple(render_id(page) for page in pages_found if render_id(page) not in svgs)


def _sheet_extras(
    model: Model, sheet: SheetRow, page: PageId, entry: OutlineSheet, known: set[PageId]
) -> tuple[str, str, str]:
    """The page's numbering argument, what precedes its image (label, marks) and its links."""
    numbering, start = sheet_label(entry.number)
    return numbering, f"{start}{sheet_mark(entry)}", page_links(model, page, sheet, known)


def schematic_source(  # noqa: PLR0913, PLR0917 -- the document, its paper, pages, drawings and backgrounds
    model: Model,
    record: DocumentRow,
    sheet: SheetRow,
    pages_found: tuple[PageId, ...],
    svgs: Mapping[str, str],
    sheets: Mapping[SheetKey, SheetBackground],
) -> str:
    """The SCHEMATIC section: full-bleed pages, `n / N` counted per drawing set."""
    kind = PageKind.SCHEMATIC
    if not pages_found or schematic_missing_keys(pages_found, svgs):
        margin = text_margin(sheet)
        back = page_background(model, record, sheets, SheetKey(record.id, kind, None))
        return f"#page(margin: {margin}, background: {back})[{RESTART}\n{NO_DRAWINGS}]"
    blocks = []
    outline = outline_sheets(model, pages_found)
    known = set(pages_found)
    for index, (page, entry) in enumerate(zip(pages_found, outline, strict=True)):
        image = f'#image(bytes({literal(svgs[render_id(page)])}), format: "svg")'
        back = page_background(model, record, sheets, SheetKey(record.id, kind, index))
        numbering, before, links = _sheet_extras(model, sheet, page, entry, known)
        blocks.append(f"#page(margin: 0mm, background: {back}{numbering})[{before}{image}{links}]")
    return "\n#pagebreak()\n".join(blocks)


def block_missing_keys(
    blocks: tuple[CableBlockRef, ...], svgs: Mapping[str, str]
) -> tuple[str, ...]:
    """The keys of `blocks` that `svgs` has no entry for, as `schematic_missing_keys` does."""
    return tuple(block.key for block in blocks if block.key not in svgs)


def _cable_runs(  # noqa: PLR0913, PLR0917 -- the document, its paper, blocks, drawings and backgrounds
    model: Model,
    record: DocumentRow,
    sheet: SheetRow,
    blocks: tuple[CableBlockRef, ...],
    svgs: Mapping[str, str],
    sheets: Mapping[SheetKey, SheetBackground],
) -> str:
    """One page run per part (pdf-0020); each run's title block names the part number.

    A block with no SVG is left out: `check` reports it, and only intermediates show the page.
    """
    runs = []
    for index, run in enumerate(cable_runs(blocks)):
        bodies = [
            f'#image(bytes({literal(svgs[block.key])}), format: "svg")'
            for block in run.blocks
            if block.key in svgs
        ]
        line = run.blocks[0].line if run.blocks[0].mpn else run.heading
        key = SheetKey(record.id, PageKind.HARNESS_DRAWING, index)
        runs.append(
            run_page(sheet, index, line, page_background(model, record, sheets, key), bodies)
        )
    return "\n#pagebreak()\n".join(runs)


def harness_drawing_source(  # noqa: PLR0913, PLR0917 -- the document, its paper, cables, drawings and backgrounds
    model: Model,
    record: DocumentRow,
    sheet: SheetRow,
    cables_found: tuple[HarnessCable, ...],
    svgs: Mapping[str, str],
    sheets: Mapping[SheetKey, SheetBackground],
) -> str:
    """Cable block pages, one run per part (pdf-0020, pdf-0022); `""` for SYSTEM with no cable."""
    if system_has_no_top_level_cables(model, record.id, cables_found):
        return ""
    blocks = cable_blocks(model, record.id, cables_found)
    if not blocks:
        margin = text_margin(sheet)
        key = SheetKey(record.id, PageKind.HARNESS_DRAWING, None)
        back = page_background(model, record, sheets, key)
        return f"#page(margin: {margin}, background: {back})[{RESTART}\n{NO_DRAWINGS}]"
    return _cable_runs(model, record, sheet, blocks, svgs, sheets)
