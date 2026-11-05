"""A hanging: a box that stands at a pin and is kept clear like a footprint (layout-0395)."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, NamedTuple

from .clearance import Keep
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .values import PinRef, Side

# The 9 fine hanging kinds and the "wire" of a foreign attachment column (R1022), and the coarse `Keep.kind` each is kept as (K6).
KEEP_KIND = MappingProxyType(
    {
        "tag": "marker",
        "arrow": "marker",
        "copy": "marker",
        "stub": "marker",
        "star": "marker",
        "flag": "marker",
        "lead": "lead",
        "anchor": "anchor",
        "dot": "dot",
        "wire": "wire",
    }
)


class Hanging(NamedTuple):
    """A box at `pin`; `side` is the pin's turned side (an input); `box_rel` is from the pin."""

    pin: PinRef
    side: Side
    box_rel: Box
    kind: str


def hanging_keep(h: Hanging, pin_at: tuple[int, int], owner: str, net: str | None) -> Keep:
    """The keep of one hanging: its box shifted to `pin_at`, absolute y, kind through the map."""
    b = h.box_rel
    return Keep("", Box(b.x + pin_at[0], b.y + pin_at[1], b.w, b.h), KEEP_KIND[h.kind], owner, net)


def hung_keeps(hung: Mapping[str, tuple[Box, ...]]) -> tuple[Keep, ...]:
    """The marker keeps of a page's hangings, absolute, by owner symbol: what markers clear and routed wires avoid (layout-0547)."""
    return tuple(Keep("", box, "marker", sym) for sym, boxes in hung.items() for box in boxes)
