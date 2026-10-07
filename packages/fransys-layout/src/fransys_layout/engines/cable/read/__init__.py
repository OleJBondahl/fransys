"""Cable engine, reading: the model's cable blocks to the placer's facts (CT5 CD2, CD5 to CD11).

The only place, with `write/`, where the cable engine meets the model vocabulary. `drawable`
is the one test of what the engine draws; `facts.py` reads the widths and flags.
"""

from fransys_layout.engines.cable.read.facts import block_facts
from fransys_layout.engines.cable.read.subjects import block_pairs, drawable
lazy from fransys_layout.engines.cable.values import BlockFacts
lazy from fransys_model.kernel import Model

__all__ = ("drawable", "read_blocks")


def read_blocks(model: Model) -> tuple[BlockFacts, ...]:
    """One `BlockFacts` per (reading, subject) the engine can draw whole, in print order.

    Absolute readings first, then each unit's; an undrawable block gets no facts and no finding.
    """
    return tuple(
        block_facts(model, subject, unit)
        for unit, subject in block_pairs(model)
        if drawable(model, subject, unit)
    )
