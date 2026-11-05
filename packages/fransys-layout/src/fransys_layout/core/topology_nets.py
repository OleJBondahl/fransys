"""Stage 1, part 5: leftover nets become attachments, fans (one per bundle) or cross-links."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .flow_values import Attach, CrossLink, Fan
from .net_keys import is_lone_cut
from .topology_fans import Att, FanDraft, LaneDraft, Slot, attached_pin, classify, deal, resolve, turn_foot_hub
from .values import Finding, PinRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .sym_values import Sym
    from .topology_chains import Link
    from .topology_elements import Elem, NetEnd
    from .values import Bundle

MIN_ATTS = 2

Parts = dict[str, list[tuple[int, str, FanDraft]]]
Attached = dict[tuple[str, int, str], PinRef]


@dataclass(frozen=True, slots=True)
class FanEnv:
    """What the fan stage reads: lane slots, lanes, elements, symbols, and net id to bundle."""

    slot: Slot
    lanes: list[LaneDraft]
    elems: dict[str, Elem]
    syms: dict[str, Sym]
    bundle_of: dict[str, Bundle]
    one_side: bool = False  # Options.bundle_direction: a bundle's box takes one side
    apart: frozenset[str] = frozenset()  # symbols dealt to their own column, not a leg lane
    cut: frozenset[str] = frozenset()  # nets with an end outside the set: a bundled one fans alone
    tag_across: bool = False  # Options.tag_across_body: a pin on the other side of the column's body is a tag pair


def fans_of(
    ends_by_net: Mapping[str, tuple[NetEnd, ...]], links: Mapping[str, Link], env: FanEnv
) -> tuple[tuple[Fan, ...], tuple[CrossLink, ...], Attached, tuple[Finding, ...]]:
    """Leftover nets: box-pin attachments, fans with dealt hubs, bundles folded, or cross-links; a tag pair is a finding."""
    parts: Parts = {}
    cross: list[tuple[str, list[NetEnd], tuple[str, ...]]] = []
    attached: Attached = {}
    held: dict[tuple[str, int, str], tuple[str, tuple[NetEnd, ...]]] = {}  # the net and ends of each attachment
    for net in (n for n in ends_by_net if n not in links):
        ends = ends_by_net[net]
        pin = attached_pin(ends)
        if pin is not None:
            _lane_through(net, ends, env)
            key = _attach_key(ends, env)
            attached[key], held[key] = pin, (net, ends)
        elif (split := _spans(ends, env.syms) if env.tag_across else ()) or not _fan_net(net, ends, parts, env):
            _lane_through(net, ends, env)
            cross.append((net, _cross_ends(ends, env.elems), split))
    fans = tuple(_fan(_merged(key, items, one_side=env.one_side)) for key, items in parts.items())
    return (fans, *_links(cross, attached, held, env))


def _links(
    cross: Sequence[tuple[str, Sequence[NetEnd], tuple[str, ...]]],
    attached: Attached,
    held: Mapping[tuple[str, int, str], tuple[str, Sequence[NetEnd]]],
    env: FanEnv,
) -> tuple[tuple[CrossLink, ...], Attached, tuple[Finding, ...]]:
    """The cross-links, then a tagged one for each attachment across its body, which leaves `attached`.

    Each box with a tagged net gets one TAG_ACROSS_BODY finding: the one place that decides the tag pair says so.
    """
    apart = _across(attached, held, env.syms) if env.tag_across else []
    wires = tuple(cross_link(net, ends, env.lanes, tagged=bool(split)) for net, ends, split in cross)
    tags = tuple(cross_link(*held[key], env.lanes, tagged=True) for key in apart)
    boxes = dict.fromkeys([*(b for _, _, split in cross for b in split), *(attached[k].sym for k in apart)])
    found = tuple(Finding("TAG_ACROSS_BODY", f"{b.partition(' ')[0]}: a net between its halves is drawn as a tag pair", None, b) for b in boxes)
    return (*wires, *tags), {k: v for k, v in attached.items() if k not in apart}, found


def _side(syms: Mapping[str, Sym], pin: PinRef) -> str:
    """The side of its body a box pin stands on."""
    return next(p.side for p in syms[pin.sym].pins if p.id == pin.pin)


def _terminal(ends: Sequence[NetEnd], syms: Mapping[str, Sym]) -> bool:
    """Whether the net has a terminal end: a terminal copies per page, never a tag (TERMINAL-COPIES)."""
    return any(syms[e.pin.sym].row_group is not None for e in ends)


def _spans(ends: Sequence[NetEnd], syms: Mapping[str, Sym]) -> tuple[str, ...]:
    """The bodies whose box pins this terminal-free net holds on both sides: it is no wire round the body."""
    if _terminal(ends, syms):
        return ()
    sides: dict[str, set[str]] = {}
    for e in (e for e in ends if e.elem is None):  # a box pin stands in no element
        sides.setdefault(e.pin.sym, set()).add(_side(syms, e.pin))
    return tuple(box for box, s in sides.items() if len(s) > 1)


def _across(
    attached: Attached, held: Mapping[tuple[str, int, str], tuple[str, Sequence[NetEnd]]], syms: Mapping[str, Sym]
) -> list[tuple[str, int, str]]:
    """The terminal-free attachments whose box pin stands on the other side of its body than the column's first one.

    The first is the head's, then the foot's, in lane order (pack.attachments): the column hangs
    from it, so a pin on the opposite side is met by a tag pair, not a wire round the body.
    """
    first: dict[tuple[str, str], str] = {}
    out = []
    for where in ("head", "foot"):
        for key in (k for k in attached if k[2] == where):
            pin = attached[key]
            if first.setdefault((key[0], pin.sym), _side(syms, pin)) != _side(syms, pin) and not _terminal(held[key][1], syms):
                out.append(key)
    return out


def _attach_key(ends: tuple[NetEnd, ...], env: FanEnv) -> tuple[str, int, str]:
    """The lane slot of the end that is no box pin: (column, index, head or foot)."""
    end = next(e for e in ends if e.site != "boxpin")
    lane, where = env.slot[(end.elem or "", env.elems[end.elem or ""].n_pin or "" if end.site == "through" else end.pin.pin)]
    return lane.column, lane.index, where


def _lane_through(net: str, ends: tuple[NetEnd, ...], env: FanEnv) -> None:
    """A through end wired to another end stands in a lane of its own, whatever its net becomes (RL-W2, layout-0486)."""
    through = next((e for e in ends if e.site == "through"), None)
    pin = next((e.pin for e in ends if e.site != "through"), None)
    if through is None or pin is None or (key := (through.elem or "", env.elems[through.elem or ""].n_pin or "")) in env.slot:
        return  # an element stands once, keyed by its n pin whichever pin its nets use
    made = deal(FanDraft("f:x", [net], [Att(None, "boxpin", pin)], []), [key[0]], env.elems, "c:", env.apart)
    env.lanes.extend(made)
    env.slot[key] = (made[0], "head" if through.pin.pin == key[1] else "foot")


def fans_split(
    ends_by_net: Mapping[str, tuple[NetEnd, ...]], links: Mapping[str, Link], env: FanEnv
) -> tuple[tuple[Fan, ...], tuple[CrossLink, ...], Attached, tuple[Finding, ...]]:
    """`fans_of` with the symbols a trial deal splits over two columns dealt apart (R283)."""
    return fans_of(ends_by_net, links, replace(env, apart=_split_symbols(ends_by_net, links, env)))


def _split_symbols(ends_by_net: Mapping[str, tuple[NetEnd, ...]], links: Mapping[str, Link], env: FanEnv) -> frozenset[str]:
    """Symbols a trial deal puts in two columns, by lane index: they take their own (R283)."""
    if len({e.sym for e in env.elems.values()}) == len(env.elems):
        return frozenset[str]()
    slot, lanes = deepcopy((env.slot, env.lanes))
    fans_of(ends_by_net, links, replace(env, slot=slot, lanes=lanes))
    cols: dict[str, set[str]] = {}
    for lane in lanes:
        for c in lane.cells:
            cols.setdefault(c.sym, set()).add(lane.column)
    return frozenset(sym for sym, homes in cols.items() if len(homes) > 1)


def _cross_ends(ends: tuple[NetEnd, ...], elems: Mapping[str, Elem]) -> list[NetEnd]:
    """The ends a cross-link joins; a net alone on one element's pins is a bridge between them."""
    if len(ends) != 1 or ends[0].elem is None or ends[0].site != "through":
        return list(ends)
    one, elem = ends[0], elems[ends[0].elem]
    return [replace(one, pin=PinRef(one.pin.sym, p)) for p in (elem.n_pin, elem.s_pin) if p]


def _facing(ends: Sequence[NetEnd], elems: Mapping[str, Elem]) -> dict[str, str]:
    """The pin each free-sided through end meets its net on (any pin may leave, so the cell turns to it)."""
    return {e.pin.sym: e.pin.pin for e in ends if e.site == "through" and e.elem and elems[e.elem].form == "free"}


def _fan_net(net: str, ends: tuple[NetEnd, ...], parts: Parts, env: FanEnv) -> bool:
    """Deal one net into its fan with its lane index (a bundle shares a fan); False: cross-link."""
    drivers, legs, throughs, is_cross = classify(ends, env.slot, env.syms)
    bundle = env.bundle_of.get(net)
    # R499: the one cut end of a bundled net is a lane of its bundle's fan
    alone = bundle is not None and is_lone_cut(is_cut=net in env.cut, pin_count=len(ends))
    if is_cross or len(drivers) + len(legs) + len(throughs) < (1 if alone else MIN_ATTS):
        return False
    key = bundle.id if bundle else net
    one = FanDraft(f"f:{key}", [net], drivers, legs)
    rest = _stand_hubs(one, ends, env)
    env.lanes.extend(deal(one, rest, env.elems, "c:", env.apart))
    turn_foot_hub(one, _facing(ends, env.elems))
    _register_hubs(one, rest, env)
    one.drivers = [replace(a, net=net) for a in one.drivers]  # each attach carries its net
    one.legs = [replace(a, net=net) for a in one.legs]
    parts.setdefault(key, []).append((bundle.pole if bundle else 0, net, one))
    return True


def _stand_hubs(one: FanDraft, ends: tuple[NetEnd, ...], env: FanEnv) -> list[str]:
    """Through elements with no cell yet; one already standing is this net's driver, at the pin the net uses."""
    rest: list[str] = []
    for e in ends:
        if e.site != "through" or not e.elem:
            continue
        hit = env.slot.get((e.elem, env.elems[e.elem].n_pin or ""))
        if hit is None:
            rest.append(e.elem)
        else:
            one.drivers.append(Att(hit[0], "hub-head", e.pin))
    return rest


def _register_hubs(one: FanDraft, throughs: Sequence[str], env: FanEnv) -> None:
    """Record the lane each dealt through element heads, so its later nets find it: an element stands once."""
    by_cell = {(env.elems[t].sym, env.elems[t].n_pin): t for t in throughs}
    for att in one.legs:
        if att.lane and att.lane.cells and (t := by_cell.get((att.lane.cells[0].sym, att.lane.cells[0].top_pin))):
            env.slot.setdefault((t, env.elems[t].n_pin or ""), (att.lane, "head"))


def _merged(key: str, parts: Sequence[tuple[int, str, FanDraft]], *, one_side: bool) -> FanDraft:
    """One fan from its nets: hub from the first net that has one; nets, drivers and legs by lane index, then in the order given (layout-0465).

    The caller's poles may skip an index; the fan has one lane per pole in use (BUNDLE).
    """
    # nets[j] is the net of lane j: the lane lines and drops name their nets by it.
    by_id = list(parts)
    ordered = sorted(by_id, key=lambda p: p[0])
    lane_of = {pole: i for i, pole in enumerate(dict.fromkeys(p for p, _, _ in ordered))}
    by_id = [(lane_of[pole], net, one) for pole, net, one in by_id]
    by_pole = [(lane_of[pole], net, one) for pole, net, one in ordered]
    parts = by_pole
    leg_box = _box_sides(by_pole) if one_side and len(parts) > 1 else {}
    ends = [(pole, a, leg) for pole, _, one in by_pole for a, leg in _sided(one, leg_box)]
    drivers = [replace(a, pole=pole) for pole, a, leg in ends if not leg]
    legs = [replace(a, pole=pole) for pole, a, leg in ends if leg]
    hub = next((one.hub for _, _, one in by_id if one.hub), None)
    nets = [net for _, net, _ in by_pole]
    return FanDraft(f"f:{key}", nets, drivers, legs, hub, len(lane_of))


def _box_sides(by_pole: Sequence[tuple[int, str, FanDraft]]) -> dict[str, bool]:
    """Box symbol to whether it is a bundle leg, by its lowest lane index (BUNDLE)."""
    out: dict[str, bool] = {}
    for _, _, one in by_pole:
        for a, leg in _sided(one, {}):
            if box := _box_of(a):
                out.setdefault(box, leg)
    return out


def _box_of(a: Att) -> str | None:
    """The box symbol an end attaches to, or None when the end is not on a box pin."""
    return a.pin.sym if a.where == "boxpin" and a.pin else None


def _sided(one: FanDraft, leg_box: Mapping[str, bool]) -> list[tuple[Att, bool]]:
    """Each end of a net with whether it is a leg; a bundle's box pins take the box's one side."""
    both = [*((a, False) for a in one.drivers), *((a, True) for a in one.legs)]
    return [(a, leg_box.get(box, leg) if (box := _box_of(a)) else leg) for a, leg in both]


def _fan(d: FanDraft) -> Fan:
    """The trunk lies above the legs; a fan whose only leg is a hub under a driver lies below."""
    side = "above" if any(a.where in ("head", "after-hub", "boxpin") for a in d.legs) else "below"
    drivers = tuple(resolve(a) for a in d.drivers)
    legs = tuple(resolve(a) for a in d.legs)
    head = drivers[0] if len(drivers) == 1 else None  # the head policy, made once here
    return Fan(d.id, tuple(d.nets), drivers, legs, d.hub, d.lanes, side, head=head)


def cross_link(net: str, ends: Sequence[NetEnd], lanes: Sequence[LaneDraft], *, tagged: bool = False) -> CrossLink:
    """The net as a wire between its ends: a lane cell, or a box pin; `tagged`: a tag pair instead."""
    where = {c.sym: (lane.column, lane.index, i) for lane in lanes for i, c in enumerate(lane.cells)}
    out = []
    for e in ends:
        col, lane_index, cell = where.get(e.pin.sym, (None, 0, 0))
        out.append(resolve(Att(None, "boxpin", e.pin, net=net)) if col is None else Attach(col, lane_index, cell, e.pin, net=net))
    return CrossLink(net, tuple(out), tagged)
