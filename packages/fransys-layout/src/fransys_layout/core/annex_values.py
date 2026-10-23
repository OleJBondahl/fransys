"""The annex values: a box with its candidate spots, and the box once placed (R345, R353).

They live apart from `annex` so `values` can name `Annex` without an import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .values import Box, Orientation, Size

__all__ = ("Annex", "AnnexBox", "Spot")


@dataclass(frozen=True, slots=True)
class Spot:
    """A place for an annex: the box's top-left offset (dx, dy) from a corner of the owner's body.

    `corner` is the body corner the offsets count from (R353). A stack grows by the box heights
    before it: `down` adds them to y, `up` takes them off. `clear` is the distance the box keeps
    beside the wire of the pins on the body edge it stands on; 0 keeps none.
    """

    name: str
    corner: Literal["TL", "TR", "BL", "BR"]
    dx: int
    dy: int
    grow: Literal["down", "up"]
    clear: int = 0


@dataclass(frozen=True, slots=True)
class Annex:
    """A box of `size` that stands at one of `spots` of its owner, by the owner's turn."""

    owner: str
    size: Size
    stack: str | None
    spots: Mapping[Orientation, tuple[Spot, ...]]


@dataclass(frozen=True, slots=True)
class AnnexBox:
    """An annex placed: its owner, page, absolute box and the spot it stands at."""

    owner: str
    page: int
    box: Box
    spot: str
