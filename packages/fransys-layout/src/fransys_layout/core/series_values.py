"""Series and parallel parts of the placer core (SERIES-PARALLEL SP3); a leaf is a symbol id.

Split from values.py as sym_values.py is (layout-0316); frozen plain data. The core sorts nothing
in it: the caller gives every order.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Series:
    """Parts in signal direction, source first: one column.

    `anchor` names the end a box-drawn function stands beyond (FLOW-DOWN, layout-0396): the first
    part for "head", the last for "tail". el computes it; the core only reads it.
    """

    parts: tuple[SeriesPart, ...]
    anchor: Literal["head", "tail"] | None = None


@dataclass(frozen=True, slots=True)
class Parallel:
    """Parts side by side in the given order, joined at both ends."""

    parts: tuple[SeriesPart, ...]


type SeriesPart = str | Series | Parallel
