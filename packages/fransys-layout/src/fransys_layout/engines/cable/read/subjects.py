"""The cable engine's blocks and the one predicate that says which of them it draws."""

from typing import Any

from fransys_model.derive.cable_drawing import block_drawn
lazy from fransys_model.kernel import Id, Model


def drawable(model: Model, subject: Id[Any], unit: Id[Any] | None) -> bool:
    """Whether the engine draws the block of `subject` in `unit`'s reading: the one predicate.

    A block has a cable or a single wire; only CD-H6 (overlapping cable boxes) is refused, by the
    placer.
    """
    return block_drawn(model, subject, unit)
