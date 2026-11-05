"""The cable engine: one pass from a model to its cable drawing blocks."""

from typing import TYPE_CHECKING

from fransys_layout.engines.cable.place import place_block
from fransys_layout.engines.cable.read import block_key, read_blocks
from fransys_layout.engines.cable.values import CableLayout

if TYPE_CHECKING:
    from fransys_layout.symbols import SymbolLibrary
    from fransys_model.kernel import Model


def lay_out_cables(model: Model, library: SymbolLibrary) -> CableLayout:
    """Return every cable block of `model` that `drawable` admits and whose lower band routes.

    Pure. Blocks stand in the reader's order; any other block is absent, and the pdf check stops
    an export that asks for it. Each block is page-less, in G from its top-left corner.
    """
    placed = (place_block(facts) for facts in read_blocks(model, library))
    return CableLayout(blocks=frozendict({block_key(b): b for b in placed if b is not None}))
