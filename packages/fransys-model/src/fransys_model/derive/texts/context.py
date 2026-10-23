"""`PrintContext`: where a text is printed, which decides what prefix it drops (design 7.7)."""

from dataclasses import dataclass
from enum import Enum

lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit


class Scope(Enum):
    """Which aspect nodes a designation drops: none, all but a unit's own, or its common cut."""

    WHOLE = "whole"
    UNIT_OWN = "unit_own"
    BELOW_COMMON = "below_common"


@dataclass(frozen=True, slots=True)
class PrintContext:
    """The unit whose reading a text is printed in and the location its ends print against.

    `reading` drops that unit's own tag; `location` the location prefix at and above it; `board`
    that board's label and all above it. `scope` picks the node rule (EL-9).
    """

    reading: Id[Unit] | None = None
    location: Id[AspectNode] | None = None
    board: Id[Item] | None = None
    scope: Scope = Scope.WHOLE
