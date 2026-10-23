"""Stage 3, seating: a card with no column stands beside the fan block it is wired to (layout-0288).

A box wired by trunks alone is a card block with `columns=()` (layout-0283). It takes the place
right after the fan block that most trunk ends at the box reach, the smaller natural key of the
block id breaking a tie. With no such block, and no box-to-box hop, it stands at the unit's end
in a row of its own, as does a box of a chain that stage 1 refused (CHAIN_REFUSED, 0289, R348):
a refusal degrades to a drawing plus a finding. Stage 4 cuts only seated cards.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from .keys import natural_key

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .values import Block, BlockList, FlowGraph


def is_bare(block: Block) -> bool:
    """The one place that asks whether a block is a card with no column."""
    return block.is_card and not block.columns


def is_chain_box(box: str | None, flow: FlowGraph) -> bool:
    """True when a trunk joins the box to nothing but boxes: one hop of a chain."""
    for fan in flow.fans:
        attached = [*fan.drivers, *fan.legs]
        if all(a.column is None for a in attached) and any(a.pin.sym == box for a in attached):
            return True
    return False


def seat_bare_cards(unit: BlockList, flow: FlowGraph) -> BlockList:
    """The unit with each column-less card moved beside its fan block, or to the end."""
    bare = sorted((b for b in unit.blocks if is_bare(b)), key=lambda b: natural_key(b.id))
    if not bare:
        return unit
    rest = [b for b in unit.blocks if not is_bare(b)]
    after: dict[str, list[Block]] = {}
    end: list[Block] = []
    for card in bare:
        host = _host(card, rest, flow)
        if host is not None:
            after.setdefault(host.id, []).append(replace(card, seat="beside"))
        elif is_chain_box(card.anchor, flow):
            end.append(replace(card, seat="beside"))
        else:
            end.append(replace(card, seat="alone"))
    out = [x for b in rest for x in (b, *after.get(b.id, ()))]
    return replace(unit, blocks=(*out, *end))


def _host(card: Block, blocks: Sequence[Block], flow: FlowGraph) -> Block | None:
    """The fan block most trunk ends at the card's box reach; None when no fan block has one."""
    ends: Counter[str] = Counter()
    for fan in flow.fans:
        attached = [*fan.drivers, *fan.legs]
        n = sum(1 for a in attached if a.column is None and a.pin.sym == card.anchor)
        cols = {a.column for a in attached if a.column}
        for b in blocks:
            if n and b.fan is not None and cols & set(b.columns):
                ends[b.id] += n
    if not ends:
        return None
    best = min(ends, key=lambda i: (-ends[i], natural_key(i)))
    return next(b for b in blocks if b.id == best)
