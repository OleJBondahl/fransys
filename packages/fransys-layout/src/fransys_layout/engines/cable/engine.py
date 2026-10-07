"""The cable engine: one pass from a model to its cable drawing blocks (CT5 CD2)."""

from typing import TYPE_CHECKING

from fransys_layout.engines.cable.place import place_block
from fransys_layout.engines.cable.read import read_blocks
from fransys_layout.engines.cable.write import write_cables

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Model


def lay_out_cables(model: Model) -> tuple[Model, tuple[Finding, ...]]:
    """Return `model` with the records of every cable block it can draw whole, and no findings.

    Pure. One block per reading and subject that `drawable` admits and whose lower band routes;
    any other gets none, and the pdf check stops an export that asks for one. The records are
    page-less, in G from the block's corner, and the pass replaces only `CABLE_KINDS`.
    """
    placed = (place_block(facts) for facts in read_blocks(model))
    blocks = tuple(block for block in placed if block is not None)
    return write_cables(model, blocks), ()
