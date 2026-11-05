"""Cable engine, reading: the model's cable blocks to the placer's facts.

The only place where the cable engine meets the model vocabulary. `drawable`
is the one test of what the engine draws; `facts.py` reads the widths and flags.
"""

from fransys_layout.engines.cable.read.facts import block_facts
from fransys_layout.engines.cable.read.subjects import block_pairs, drawable
from fransys_model.derive.cable_drawing import cable_block_key
lazy from fransys_layout.engines.cable.values import BlockFacts, PlacedBlock
lazy from fransys_layout.symbols import SymbolLibrary
lazy from fransys_model.kernel import Model

__all__ = ("block_key", "drawable", "read_blocks")


def read_blocks(model: Model, library: SymbolLibrary) -> tuple[BlockFacts, ...]:
    """One `BlockFacts` per (reading, subject) the engine can draw whole, in print order.

    Absolute readings first, then each unit's; an undrawable block gets no facts and no finding.
    """
    return tuple(block_facts(model, subject, unit, library) for unit, subject in block_pairs(model) if drawable(model, subject, unit))


def block_key(block: PlacedBlock) -> str:
    """The key of a placed block: `cable_block_key` of its reading and subject."""
    return cable_block_key(block.unit, block.subject)
