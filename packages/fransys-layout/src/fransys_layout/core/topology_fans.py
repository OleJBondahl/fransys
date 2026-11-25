"""Stage 1, part 3: leftover nets become fans or cross-links; through elements are dealt to legs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .errors import CoreError
from .flow_values import Attach, Cell, Fan
from .values import PinRef
lazy from .sym_values import Sym

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .topology_elements import Elem, NetEnd

PAIR = 2
Slot = dict[tuple[str, str], tuple["LaneDraft", str]]


@dataclass(slots=True)
class LaneDraft:
    """A lane under construction: column id, lane index, cells; hubs change cells first."""

    column: str
    index: int
    cells: list[Cell]
    offset: int = 0
    hops: tuple[tuple[str, ...], ...] = field(default=(), kw_only=True)


@dataclass(frozen=True, slots=True)
class Att:
    """An attachment before cell indexes are final: a lane end, a hub position, or a box pin."""

    lane: LaneDraft | None
    where: str
    pin: PinRef | None = None
    pole: int = 0
    net: str | None = None


@dataclass(slots=True)
class FanDraft:
    id: str
    nets: list[str]
    drivers: list[Att] = field(default_factory=list)
    legs: list[Att] = field(default_factory=list)
    hub: str | None = None
    lanes: int = 1


def attached_pin(ends: tuple[NetEnd, ...]) -> PinRef | None:
    """A two-end net of one box pin and one lane end or through end is an attachment, not a fan."""
    if len(ends) == PAIR:
        roles = {e.site for e in ends}
        if roles in ({"boxpin", "top"}, {"boxpin", "bottom"}, {"boxpin", "through"}):
            return next(e.pin for e in ends if e.site == "boxpin")
    return None


def _south(pins: Iterable[PinRef], syms: Mapping[str, Sym]) -> set[PinRef]:
    return {p for p in pins if next(q.side for q in syms[p.sym].pins if q.id == p.pin) == "S"}


def plumbed(fans: Sequence[Fan], attached: Mapping[tuple[str, int, str], PinRef], syms: Mapping[str, Sym]) -> dict[tuple[str, int, str], PinRef]:
    """The first load of each net of a fan with one S box-pin driver is attached to that pin, as a direct chain is (PARALLEL-FIRST-PLUMB).

    The first leg is the first by designation. A column that holds a box pin already is left alone, and so is a box whose S pins
    carry another fan or attachment: the first leg's trunk would run over that pin's drop (KI-216).
    """
    taken = {k[0] for k in attached}
    out: dict[tuple[str, int, str], PinRef] = {}
    for fan in fans:
        rest = [a.pin for f in fans if f is not fan for a in f.drivers if a.column is None]
        shared = {p.sym for p in _south([*rest, *attached.values()], syms)}
        drivers = Counter(a.net for a in fan.drivers)
        for d in (a for a in fan.drivers if a.column is None and drivers[a.net] == 1 and a.pin.sym not in shared and _south([a.pin], syms)):
            first = next((a for a in fan.legs if a.net == d.net), None)
            if first is not None and first.column is not None and first.column not in taken and first.cell == 0:
                out[first.column, first.lane, "head"] = d.pin
    return out


def classify(ends: tuple[NetEnd, ...], slot: Slot, syms: Mapping[str, Sym]) -> tuple[list[Att], list[Att], list[str], bool]:
    """Drivers drop to the trunk from above, legs hang below; an off-lane end is a cross-link."""
    drivers: list[Att] = []
    legs: list[Att] = []
    throughs = [e.elem or "" for e in ends if e.site == "through"]
    cross = False
    for e in (x for x in ends if x.site != "through"):
        found = _att_of(e, slot, syms)
        if found is None:
            cross = True
        else:
            (legs if found[0] else drivers).append(found[1])
    return drivers, legs, throughs, cross


def _own_only(end: NetEnd) -> bool:
    return bool(end.far) and {p.sym for p in end.far} == {end.pin.sym}


def own_wired(ends: tuple[NetEnd, ...]) -> list[tuple[NetEnd, NetEnd]]:
    """Each end whose conductors run only to pins of its own symbol, with every end it is wired to: a join, not a trunk attachment.

    A pair of two such ends is joined once, from the earlier end.
    """
    return [
        (e, mate)
        for i, e in enumerate(ends)
        if e.site != "through" and _own_only(e)
        for j, mate in enumerate(ends)
        if mate.pin in e.far and (j > i or not _own_only(mate))
    ]


def _att_of(end: NetEnd, slot: Slot, syms: Mapping[str, Sym]) -> tuple[bool, Att] | None:
    """(is a leg, the attachment) of one end, or None when it is off a lane end."""
    if end.site == "boxpin":
        side = next(p.side for p in syms[end.pin.sym].pins if p.id == end.pin.pin)
        return side != "S", Att(None, "boxpin", end.pin)
    hit = slot.get((end.elem or "", end.pin.pin))
    if hit is None:
        return None
    lane, where = hit
    return where == "head", Att(lane, where)


def deal(
    fan: FanDraft,
    throughs: Sequence[NetEnd],
    elems: Mapping[str, Elem],
    col_prefix: str,
    apart: frozenset[str] = frozenset(),
) -> tuple[LaneDraft, ...]:
    """Hub rule: a through stands between the trunk and a leg only with conductors to the leg's head pin and to another end of the net.

    With that one conductor it stands over the trunk at that leg, as a hub does; the rest stand in lanes of their own (CHAIN-FROM-HEAD).
    A hub with no lane to stand in (the first attachment is a box pin) is dealt like the rest. Returns the lanes it made, `apart` ones too (R283).
    """
    held = [elems[t.elem or ""] for t in throughs]
    cells = [Cell(e.sym, "R0", e.n_pin, e.s_pin) for e in held]
    far = {e.sym: t.far for e, t in zip(held, throughs, strict=True)}
    apart = _own_symbols(fan, held, elems, apart)
    own = [c for c in cells if c.sym in apart]
    cells = [c for c in cells if c.sym not in apart]
    if not cells and not own:
        return ()
    if cells and (hub := _hub_at_head(fan, cells, far)):
        cells.remove(hub)
    elif cells and fan.drivers and not fan.legs and _hub_at_foot(fan, cells[0]):
        cells.pop(0)
    rest = [*_deal_to_legs(fan, cells, far), *own]
    made = tuple(LaneDraft(f"{col_prefix}{cell.sym}", 0, [cell]) for cell in rest)
    fan.legs.extend(Att(lane, "head") for lane in made)
    return made


def turn_foot_hub(fan: FanDraft, facing: Mapping[str, str]) -> None:
    """Turn a free-sided hub at a lane's foot, or dealt to a leg's head, to meet the fan on its `facing` pin (by symbol; R924)."""
    for lane, i in ((a.lane, -(a.where == "hub-foot")) for a in fan.legs if a.lane and a.where in ("hub-foot", "head")):  # -1 foot hub, 0 leg head
        c = lane.cells[i]
        if facing.get(c.sym, "") == c.bottom_pin:
            lane.cells[i] = Cell(c.sym, "R180", c.bottom_pin, c.top_pin, hold=c.hold)


def _own_symbols(fan: FanDraft, throughs: Sequence[Elem], elems: Mapping[str, Elem], apart: frozenset[str]) -> frozenset[str]:
    """Symbols that take their own column: the trial's, and a hub with more elements elsewhere."""
    if bool(fan.drivers) == bool(fan.legs):
        return apart
    return apart | {e.sym for e in elems.values() if e not in throughs}


def _head(lane: LaneDraft) -> PinRef:
    """The pin a lane's head cell shows to the fan."""
    return PinRef(lane.cells[0].sym, lane.cells[0].top_pin or "")


def _stands_over(fan: FanDraft, reach: AbstractSet[PinRef], lane: LaneDraft) -> bool:
    """A cell with a conductor to the lane's head pin, and to another end when the fan has one."""
    return _head(lane) in reach and (len(reach) > 1 or len(fan.drivers) + len(fan.legs) < PAIR)


def _deal_to_legs(fan: FanDraft, cells: Sequence[Cell], far: Mapping[str, AbstractSet[PinRef]]) -> list[Cell]:
    """Put each cell with a conductor to a free leg lane's head pin at that head; return the cells left over.

    One that stands over the lane meets the trunk above it. One with that conductor only stands over the trunk like a hub at a head, in a fan
    with no driver of its own: a net with drivers can leave its fan for a cross-link (y cycle), which has no trunk to stand over.
    """
    # KI-1264: with this conjunct w08 draws one junction off its line and 6 bends (DEAL-LEGS-W08)
    left = list(cells)
    for i, lane in ((i, a.lane) for i, a in enumerate(fan.legs) if a.lane is not None and a.where == "head"):
        if hit := next((c for c in left if _stands_over(fan, far[c.sym], lane)), None):
            lane.cells.insert(0, hit)
            left.remove(hit)
        elif all(d.where == "hub-head" for d in fan.drivers) and (hit := next((c for c in left if _head(lane) in far[c.sym]), None)):
            lane.cells.insert(0, hit)
            left.remove(hit)
            fan.drivers.append(Att(lane, "hub-head"))
            fan.legs[i] = Att(lane, "after-hub")
    return left


def _hub_at_head(fan: FanDraft, cells: Sequence[Cell], far: Mapping[str, AbstractSet[PinRef]]) -> Cell | None:
    """Stand the first of `cells` wired to a leg's head pin over that leg and return it; None when none is (or a driver is).

    One conductor is enough here, not in `_stands_over`: the first so wired, whatever its place in the net's order, so every lane of a fan
    meets its trunk at one stack index (PUMP-ALIGN).
    """
    for i, first in enumerate(() if fan.drivers else fan.legs):
        if (lane := first.lane) is None or not (hub := next((c for c in cells if _head(lane) in far[c.sym]), None)):
            continue
        lane.cells.insert(0, hub)
        fan.drivers.append(Att(lane, "hub-head"))
        fan.legs[i] = Att(lane, "after-hub")
        fan.hub = hub.sym
        return hub
    return None


# KI-1124
def _hub_at_foot(fan: FanDraft, hub: Cell) -> bool:
    """Stand the hub under the first driver that has a lane; False when every driver is a box pin."""
    for i, first in enumerate(fan.drivers):
        if first.lane is None:
            continue
        first.lane.cells.append(hub)
        fan.drivers[i] = Att(first.lane, "before-hub")
        fan.legs.append(Att(first.lane, "hub-foot"))
        fan.hub = hub.sym
        return True
    return False


def resolve(att: Att) -> Attach:
    """Final cell indexes and pins, once every hub has been dealt."""
    if att.net is None:
        msg = f"attachment {att.where} reached resolve with no net"
        raise CoreError(msg)
    if att.lane is None:
        if att.pin is None:
            msg = f"attachment {att.where} reached resolve with no pin"
            raise CoreError(msg)
        return Attach(None, 0, 0, att.pin, att.pole, net=att.net)
    cells = att.lane.cells
    last = len(cells) - 1
    index, top = {
        "head": (0, True),
        "foot": (last, False),
        "hub-head": (0, False),
        "after-hub": (1, True),
        "before-hub": (last - 1, False),
        "hub-foot": (last, True),
    }[att.where]
    where = att.pin or _facing(cells[index], top=top, at=att.where)
    return Attach(att.lane.column, att.lane.index, index, where, att.pole, net=att.net)


def _facing(cell: Cell, *, top: bool, at: str) -> PinRef:
    """The cell's pin on the head or foot side; a cell with none cannot be built, never an empty pin."""
    pin = cell.top_pin if top else cell.bottom_pin
    if pin is None:
        msg = f"attachment {at} on {cell.sym} has no pin on its {'head' if top else 'foot'} side: a wired pin was dropped"
        raise CoreError(msg)
    return PinRef(cell.sym, pin)
