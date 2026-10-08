"""The cable engine's blocks and the one predicate that says which of them it draws."""

from typing import Any

from fransys_model.derive.cable_drawing import block_drawn, drawn_blocks
lazy from fransys_model.kernel import Id, Model


def block_pairs(model: Model) -> tuple[tuple[Id[Any] | None, Id[Any]], ...]:
    """Every drawn (unit, subject) of the model once, in print order: `drawn_blocks`' own."""
    return drawn_blocks(model)


def drawable(model: Model, subject: Id[Any], unit: Id[Any] | None) -> bool:
    """Whether the engine draws the block of `subject` in `unit`'s reading: the one predicate.

    A block has a cable or a single wire; only CD-H6 (overlapping cable boxes) is refused, by the
    placer.
    """
    return block_drawn(model, subject, unit)
