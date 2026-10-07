"""What `check` says of a document's cable blocks (CD12, pdf-0022): a missing SVG, a block too big.

Both are `DOCUMENT_NO_DRAWINGS` messages, as a missing schematic page key is. A block is measured
in grid units, so no mm conversion lives here: `content_extent` turns the page body into the
block's own grid, the one place sheet millimetres become grid units.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.cable_drawing import cable_block_key
from fransys_model.derive.drawing_text import content_extent
from fransys_model.layout import CableBlock, layout_of, sheet_format_of

from ._cable_runs import Block, body_size_mm
from ._drawings import block_missing_keys, cable_blocks, harness_cables_for
from ._geometry import resolve_sheet_format

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Model
    from fransys_model.vocab import Document, PageKind


def _too_big_messages(
    model: Model, record: Document, pages: tuple[PageKind, ...], blocks: tuple[Block, ...]
) -> list[str]:
    """One message per block wider or taller than the document's page body (Q7).

    The block is scaled by its own sheet; the body is the document's sheet minus the run's frame.
    """
    width_mm, height_mm = body_size_mm(resolve_sheet_format(model, record, pages))
    laid = {
        cable_block_key(found.unit, found.subject): found
        for found in layout_of(model, CableBlock).values()
    }
    messages = []
    for block in blocks:
        found = laid.get(block.key)
        if found is None:
            continue
        module_mm = sheet_format_of(model, found.sheet_format).module_mm
        room = (content_extent(width_mm, module_mm), content_extent(height_mm, module_mm))
        if found.width > room[0] or found.height > room[1]:
            messages.append(
                f"HARNESS_DRAWING: block {block.key} is {found.width} x {found.height} G, "
                f"the page body holds {room[0]} x {room[1]} G"
            )
    return messages


def harness_block_messages(
    model: Model, record: Document, pages: tuple[PageKind, ...], svgs: Mapping[str, str]
) -> list[str]:
    """The `HARNESS_DRAWING` messages of blocks with no SVG or too big for the page body."""
    blocks = cable_blocks(model, record, harness_cables_for(model, record, pages))
    messages = []
    if missing := block_missing_keys(blocks, svgs):
        messages.append(f"HARNESS_DRAWING: missing drawing for {', '.join(missing)}")
    return messages + _too_big_messages(model, record, pages, blocks)
