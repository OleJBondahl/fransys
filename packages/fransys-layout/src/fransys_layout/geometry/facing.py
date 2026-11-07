"""The side a port or slot points to."""

from enum import Enum
from typing import TYPE_CHECKING

from fransys_layout.core.sides import opposite
from fransys_model.kernel import register_enum

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ("OPPOSITE", "Facing")


@register_enum
class Facing(Enum):
    """The side a port or slot points to; y grows down, so `N` is towards smaller y."""

    N = "n"
    E = "e"
    S = "s"
    W = "w"


OPPOSITE: Mapping[Facing, Facing] = frozendict({f: Facing[opposite(f.name)] for f in Facing})
