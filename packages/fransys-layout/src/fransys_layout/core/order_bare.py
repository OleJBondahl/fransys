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
    from collections.abc import Mapping, Sequence

    from .flow_values import Block, BlockList, FlowGraph


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
    """The unit with each column-less card moved beside its fan block, after its peer, or to the end.

    Tag order holds only for cards with no peer; the cards of one peer stand in its pin order.
    """
    bare = [b for b in unit.blocks if is_bare(b)]
    if not bare:
        return unit
    rest = [b for b in unit.blocks if not is_bare(b)]
    fan, peer = _hosts(bare, rest, unit, flow)
    pin = {c.id: _pin_key(c, peer[c.id], flow) for c in bare if c.id in peer}
    ordered = sorted(bare, key=lambda b: (pin.get(b.id, ()), natural_key(b.id)))
    return replace(unit, blocks=_stand(rest, ordered, fan, peer, flow))


def _hosts(bare: Sequence[Block], rest: Sequence[Block], unit: BlockList, flow: FlowGraph) -> tuple[dict[str, Block], dict[str, Block]]:
    """Each card's fan block, else the card block of its peer; a card in neither map goes to the end."""
    peers, by_anchor = _peers(flow), {b.anchor: b for b in unit.blocks if b.is_card}
    fan = {c.id: h for c in bare if (h := _host(c, rest, flow)) is not None}
    peer = {c.id: h for c in bare if c.id not in fan and (h := _peer_host(c, peers, by_anchor)) is not None}
    return fan, peer


def _stand(
    rest: Sequence[Block], ordered: Sequence[Block], fan: Mapping[str, Block], peer: Mapping[str, Block], flow: FlowGraph
) -> tuple[Block, ...]:
    """Each block of `rest`, the cards of its fan after it, each card's peer leaves after it; the rest at the end."""
    after: dict[str, list[Block]] = {}
    end: list[Block] = []
    for card in ordered:
        if card.id in fan or card.id in peer:
            after.setdefault((fan.get(card.id) or peer[card.id]).id, []).append(replace(card, seat="beside"))
        else:
            end.append(replace(card, seat="beside" if is_chain_box(card.anchor, flow) else "alone"))
    out: list[Block] = []
    for b in (*rest, *end):
        out += _with_cards(b, after)
    return tuple(out)


def _with_cards(block: Block, after: Mapping[str, Sequence[Block]]) -> list[Block]:
    """The block and the cards seated after it, each with the cards seated after that."""
    return [block, *(y for c in after.get(block.id, ()) for y in _with_cards(c, after))]


def _peers(flow: FlowGraph) -> dict[str, frozenset[str]]:
    """Each box to the other boxes its nets meet at box pins."""
    out: dict[str, set[str]] = {}
    for fan in flow.fans:
        boxes = {a.pin.sym for a in (*fan.drivers, *fan.legs) if a.column is None}
        for box in boxes:
            out.setdefault(box, set()).update(boxes - {box})
    return {box: frozenset(near) for box, near in out.items()}


def _peer_host(card: Block, peers: Mapping[str, frozenset[str]], by_anchor: Mapping[str | None, Block]) -> Block | None:
    """The one card block a card is wired to by box pins, when it is a hub: a bare peer with one more peer than leaves is a chain link (R2099).

    Of a lone pair the card with the smaller block id hosts.
    """
    near = peers.get(card.anchor or "", frozenset())
    host = by_anchor.get(next(iter(near))) if len(near) == 1 else None
    if host is None or not is_bare(host):
        return host
    around = peers.get(host.anchor or "", frozenset())
    if any(len(peers.get(q, ())) != 1 for q in around):
        return None
    return host if len(around) > 1 or host.id < card.id else None


def _pin_key(card: Block, host: Block, flow: FlowGraph) -> tuple[tuple[int, int | str], ...]:
    """The first of the host's pins that a net of the card meets, by its id."""
    fans = [(*f.drivers, *f.legs) for f in flow.fans]
    keys = [natural_key(a.pin.pin) for att in fans if any(x.pin.sym == card.anchor for x in att) for a in att if a.pin.sym == host.anchor]
    return min(keys, default=())


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
