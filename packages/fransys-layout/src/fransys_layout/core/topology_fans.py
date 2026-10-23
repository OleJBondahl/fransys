"""Stage 1, part 3: leftover nets become fans or cross-links; through elements are dealt to legs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .errors import CoreError
from .keys import natural_key
from .values import Attach, Cell, PinRef
lazy from .sym_values import Sym

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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


def classify(
    ends: tuple[NetEnd, ...], slot: Slot, syms: Mapping[str, Sym]
) -> tuple[list[Att], list[Att], list[str], bool]:
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
    throughs: Sequence[str],
    elems: Mapping[str, Elem],
    col_prefix: str,
    apart: frozenset[str] = frozenset(),
) -> tuple[LaneDraft, ...]:
    """Hub rule: with no driver the first through heads the first leg; others head the next legs.

    A hub with no lane to stand in (the first attachment is a box pin) is dealt like the rest.
    Returns the lanes it made for the cells left over, and for the `apart` symbols (R283).
    """
    cells = [
        Cell(elems[t].sym, "R0", elems[t].n_pin, elems[t].s_pin)
        for t in sorted(throughs, key=natural_key)
    ]
    apart = _own_symbols(fan, throughs, elems, apart)
    own = [c for c in cells if c.sym in apart]
    cells = [c for c in cells if c.sym not in apart]
    if not cells and not own:
        return ()
    if cells and (
        (not fan.drivers and fan.legs and _hub_at_head(fan, cells[0]))
        or (fan.drivers and not fan.legs and _hub_at_foot(fan, cells[0]))
    ):
        cells.pop(0)
    rest = [*_deal_to_legs(fan, cells), *own]
    made = tuple(LaneDraft(f"{col_prefix}{cell.sym}", 0, [cell]) for cell in rest)
    fan.legs.extend(Att(lane, "head") for lane in made)
    return made


def _own_symbols(
    fan: FanDraft, throughs: Sequence[str], elems: Mapping[str, Elem], apart: frozenset[str]
) -> frozenset[str]:
    """Symbols that take their own column: the trial's, and a hub with more elements elsewhere."""
    if bool(fan.drivers) == bool(fan.legs):
        return apart
    return apart | {e.sym for k, e in elems.items() if k not in throughs}


def _deal_to_legs(fan: FanDraft, cells: Sequence[Cell]) -> Sequence[Cell]:
    """Put one cell at the head of each free leg lane in turn; return the cells left over."""
    free_lanes = [a.lane for a in fan.legs if a.lane is not None and a.where == "head"]
    for lane, cell in zip(free_lanes, cells, strict=False):
        lane.cells.insert(0, cell)
    return cells[len(free_lanes) :]


def _hub_at_head(fan: FanDraft, hub: Cell) -> bool:
    """Stand the hub over the first leg's lane; False when that leg is a box pin (no lane)."""
    first = fan.legs[0]
    if first.lane is None:
        return False
    first.lane.cells.insert(0, hub)
    fan.drivers.append(Att(first.lane, "hub-head"))
    fan.legs[0] = Att(first.lane, "after-hub")
    fan.hub = hub.sym
    return True


def _hub_at_foot(fan: FanDraft, hub: Cell) -> bool:
    """Stand the hub under the first driver's lane; False when that driver is a box pin."""
    first = fan.drivers[0]
    if first.lane is None:
        return False
    first.lane.cells.append(hub)
    fan.drivers[0] = Att(first.lane, "before-hub")
    fan.legs.append(Att(first.lane, "hub-foot"))
    fan.hub = hub.sym
    return True


def resolve(att: Att) -> Attach:
    """Final cell indexes and pins, once every hub has been dealt."""
    if att.net is None:
        msg = f"attachment {att.where} reached resolve with no net"
        raise CoreError(msg)
    if att.lane is None:
        return Attach(None, 0, 0, att.pin, att.pole, net=att.net)  # ty: ignore[invalid-argument-type] - a box pin has its ref
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
    pin = cells[index].top_pin if top else cells[index].bottom_pin
    where = PinRef(cells[index].sym, pin or "")
    return Attach(att.lane.column, att.lane.index, index, where, att.pole, net=att.net)
