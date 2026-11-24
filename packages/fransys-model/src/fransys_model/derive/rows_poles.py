"""The row of one pole of a function: its two ends, and the line end when a stated side gives it (model-0128)."""

from typing import NamedTuple

lazy from fransys_model.vocab.templates import PortTemplate

__all__ = ["Pole"]


class Pole(NamedTuple):
    """One pole's ends: `line` is the end on `Side.A` (supply side) when the other is not, else `None`.

    `ends` is `(line, load)` when `line` is known, else the two ends in natural marking order.
    """

    line: PortTemplate | None
    ends: tuple[PortTemplate, PortTemplate]
