"""Drawing pages, shared by `document.py` and `checks.py` so they agree on "no drawings"."""

from typing import TYPE_CHECKING

from fransys_model.derive import (
    CableBlockRef,
    cable_blocks,
    cable_runs,
    continued_heading,
    harness_cables_for,
    schematic_page_ids,
    system_has_no_top_level_cables,
)
from fransys_model.derive import replica_only_sets as matched_replica_only_sets
from fransys_model.derive.page_nav import outline_sheets
from fransys_model.kernel import render_id
from fransys_model.vocab import PageKind

from ._cable_runs import run_page
from ._doc import background
from ._geometry import text_margin
from ._labels import RESTART, sheet_label
from ._links import page_links
from ._marks import sheet_mark
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import (
        DocumentRow,
        PageId,
        ReplicaOnlySet,
        SheetRow,
    )
    from fransys_model.derive.page_nav import OutlineSheet, ReferenceLink
    from fransys_model.kernel import Model

    from ._doc import Doc

NO_DRAWINGS = '#par(text("No drawings."))'


def schematic_pages(model: Model, record: DocumentRow, pages: tuple[PageKind, ...]) -> tuple[PageId, ...]:
    """The subject's drawing-set pages; empty for an item subject (no `pcb_review` yet)."""
    return schematic_page_ids(model, record.id, pages)


def replica_only_sets(model: Model, record: DocumentRow, pages: tuple[PageKind, ...]) -> tuple[ReplicaOnlySet, ...]:
    """The matched sets skipped as replica-only; empty without a location or unit subject."""
    return matched_replica_only_sets(model, record.id, pages)


def schematic_missing_keys(pages_found: tuple[PageId, ...], svgs: Mapping[str, str]) -> tuple[str, ...]:
    """The `render_id`s of `pages_found` that `svgs` has no entry for."""
    return tuple(render_id(page) for page in pages_found if render_id(page) not in svgs)


def _sheet_extras(
    model: Model,
    sheet: SheetRow,
    entry: OutlineSheet,
    links: tuple[ReferenceLink, ...],
) -> tuple[str, str, str]:
    """The page's numbering argument, what precedes its image (label, marks) and its links."""
    numbering, start = sheet_label(entry.number)
    return numbering, f"{start}{sheet_mark(entry)}", page_links(model, sheet, links)


def _no_drawings_page(doc: Doc, kind: PageKind) -> str:
    """The one `No drawings.` page of `kind`."""
    margin, back = text_margin(doc[3], doc[6]["page_margin_mm"]), background(doc, kind, None)
    return f"#page(margin: {margin}, background: {back})[{RESTART}\n{NO_DRAWINGS}]"


def schematic_source(doc: Doc, svgs: Mapping[str, str], links: Mapping[PageId, tuple[ReferenceLink, ...]]) -> str:
    """The SCHEMATIC section: full-bleed pages, `n / N` counted per drawing set."""
    model, record, pages, sheet, _, _, _ = doc
    kind = PageKind.SCHEMATIC
    pages_found = schematic_pages(model, record, pages)
    if not pages_found or schematic_missing_keys(pages_found, svgs):
        return _no_drawings_page(doc, kind)
    blocks = []
    outline = outline_sheets(model, pages_found)
    printed = {entry.destination for entry in outline}  # a link to a page not printed here dangles
    for index, (page, entry) in enumerate(zip(pages_found, outline, strict=True)):
        image = f'#image(bytes({literal(svgs[render_id(page)])}), format: "svg")'
        numbering, before, boxes = _sheet_extras(model, sheet, entry, tuple(k for k in links[page] if k.target in printed))
        back = background(doc, kind, index)
        blocks.append(f"#page(margin: 0mm, background: {back}{numbering})[{before}{image}{boxes}]")
    return "\n#pagebreak()\n".join(blocks)


def block_missing_keys(blocks: tuple[CableBlockRef, ...], svgs: Mapping[str, str]) -> tuple[str, ...]:
    """The keys of `blocks` that `svgs` has no entry for, as `schematic_missing_keys` does."""
    return tuple(block.key for block in blocks if block.key not in svgs)


def _cable_runs(doc: Doc, blocks: tuple[CableBlockRef, ...], svgs: Mapping[str, str]) -> str:
    """One page run per part (pdf-0020); each run's title block names the part number.

    A block with no SVG is left out: `check` reports it, and only intermediates show the page.
    """
    runs = []
    for index, run in enumerate(cable_runs(blocks)):
        bodies = [f'#image(bytes({literal(svgs[block.key])}), format: "svg")' for block in run.blocks if block.key in svgs]
        line = run.blocks[0].line if run.blocks[0].mpn else run.heading
        runs.append(
            run_page(
                doc,
                index,
                (line, continued_heading(doc[0], line)),
                background(doc, PageKind.HARNESS_DRAWING, index),
                bodies,
            )
        )
    return "\n#pagebreak()\n".join(runs)


def harness_drawing_source(doc: Doc, svgs: Mapping[str, str]) -> str:
    """Cable block pages, one run per part (pdf-0020, pdf-0022); `""` for SYSTEM with no cable."""
    model, record, pages, _, _, _, _ = doc
    document = record.id
    cables_found = harness_cables_for(model, document, pages)
    if system_has_no_top_level_cables(model, document, cables_found):
        return ""
    blocks = cable_blocks(model, document, cables_found)
    if not blocks:
        return _no_drawings_page(doc, PageKind.HARNESS_DRAWING)
    return _cable_runs(doc, blocks, svgs)
