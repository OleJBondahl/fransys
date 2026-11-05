"""What `check` says of a document's cable blocks (pdf-0022): a missing SVG, a block too big.

Both are `DOCUMENT_NO_DRAWINGS` messages, as a missing schematic page key is. A block is measured
in grid units, so no mm conversion lives here: `content_extent` turns the page body into the
block's own grid, the one place sheet millimetres become grid units.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.derive import (
    cable_block_sizes,
)
from fransys_model.derive.drawing_text import content_extent

from ._drawings import block_missing_keys

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import CableBlockRef
    from fransys_model.kernel import Model

    type CableSizes = Mapping[str, tuple[int, int]]  # (width, height) in G


def _too_big_messages(model: Model, blocks: tuple[CableBlockRef, ...], laid: CableSizes, body_mm: tuple[float, float]) -> list[str]:
    """One message per block wider or taller than the document's page body.

    The block is scaled by its own sheet; the body is the document's sheet minus the run's frame.
    """
    width_mm, height_mm = (Decimal(str(mm)) for mm in body_mm)
    sizes = cable_block_sizes(model, laid)
    messages = []
    for block in blocks:
        found = sizes.get(block.key)
        if found is None:
            continue
        per_division = found.mm_per_division
        room = (content_extent(width_mm, per_division), content_extent(height_mm, per_division))
        if found.width > room[0] or found.height > room[1]:
            messages.append(f"HARNESS_DRAWING: block {block.key} is {found.width} x {found.height} G, the page body holds {room[0]} x {room[1]} G")
    return messages


def harness_block_messages(
    model: Model, blocks: tuple[CableBlockRef, ...], svgs: Mapping[str, str], laid: CableSizes, body_mm: tuple[float, float]
) -> list[str]:
    """The `HARNESS_DRAWING` messages of `blocks` with no SVG or too big for the page body `body_mm`."""
    messages = []
    if missing := block_missing_keys(blocks, svgs):
        messages.append(f"HARNESS_DRAWING: missing drawing for {', '.join(missing)}")
    return messages + _too_big_messages(model, blocks, laid, body_mm)
