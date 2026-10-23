"""Stage 1, part 5: leftover nets become attachments, fans (one per bundle) or cross-links."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .keys import natural_key
from .topology_fans import Att, FanDraft, LaneDraft, Slot, attached_pin, classify, deal, resolve
from .values import Attach, CrossLink, Fan, PinRef

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


def fans_of(
    ends_by_net: Mapping[str, tuple[NetEnd, ...]], links: Mapping[str, Link], env: FanEnv
) -> tuple[tuple[Fan, ...], tuple[CrossLink, ...], Attached]:
    """Leftover nets: box-pin attachments, fans with dealt hubs, bundles folded, or cross-links."""
    parts: Parts = {}
    cross: list[tuple[str, list[NetEnd]]] = []
    attached: Attached = {}
    for net in sorted(ends_by_net, key=natural_key):
        if net in links:
            continue
        ends = ends_by_net[net]
        pin = attached_pin(ends)
        if pin is not None:
            _lane_through(net, ends, env, pin)
            attached[_attach_key(ends, env)] = pin
        elif not _fan_net(net, ends, parts, env):
            cross.append((net, _cross_ends(ends, env.elems)))
    ordered = sorted(parts.items(), key=lambda kv: natural_key(kv[0]))
    fans = tuple(_fan(_merged(key, items, one_side=env.one_side)) for key, items in ordered)
    return fans, tuple(cross_link(net, ends, env.lanes) for net, ends in cross), attached


def _attach_key(ends: tuple[NetEnd, ...], env: FanEnv) -> tuple[str, int, str]:
    """The lane slot of the end that is no box pin: (column, index, head or foot)."""
    lane, where = env.slot[next((e.elem or "", e.pin.pin) for e in ends if e.site != "boxpin")]
    return lane.column, lane.index, where


def _lane_through(net: str, ends: tuple[NetEnd, ...], env: FanEnv, pin: PinRef) -> None:
    """A through end wired to a box pin stands in a lane of its own: an attachment (RL-W2)."""
    through = next((e for e in ends if e.site == "through"), None)
    if through is None or (key := (through.elem or "", through.pin.pin)) in env.slot:
        return
    made = deal(
        FanDraft("f:x", [net], [Att(None, "boxpin", pin)], []), [key[0]], env.elems, "c:", env.apart
    )
    env.lanes.extend(made)
    env.slot[key] = (made[0], "head" if key[1] == env.elems[key[0]].n_pin else "foot")


def fans_split(
    ends_by_net: Mapping[str, tuple[NetEnd, ...]], links: Mapping[str, Link], env: FanEnv
) -> tuple[tuple[Fan, ...], tuple[CrossLink, ...], Attached]:
    """`fans_of` with the symbols a trial deal splits over two columns dealt apart (R283)."""
    return fans_of(ends_by_net, links, replace(env, apart=_split_symbols(ends_by_net, links, env)))


def _split_symbols(
    ends_by_net: Mapping[str, tuple[NetEnd, ...]], links: Mapping[str, Link], env: FanEnv
) -> frozenset[str]:
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
    wired = [e for e in ends if e.site != "through"]
    if wired or len(ends) != 1 or ends[0].elem is None:
        return wired
    one, elem = ends[0], elems[ends[0].elem]
    return [replace(one, pin=PinRef(one.pin.sym, p)) for p in (elem.n_pin, elem.s_pin) if p]


def _fan_net(net: str, ends: tuple[NetEnd, ...], parts: Parts, env: FanEnv) -> bool:
    """Deal one net into its fan with its lane index (a bundle shares a fan); False: cross-link."""
    drivers, legs, throughs, is_cross = classify(ends, env.slot, env.syms)
    bundle = env.bundle_of.get(net)
    # R499: the one cut end of a bundled net is a lane of its bundle's fan
    alone = bundle is not None and net in env.cut and len(ends) == 1
    if is_cross or len(drivers) + len(legs) + len(throughs) < (1 if alone else MIN_ATTS):
        return False
    key = bundle.id if bundle else net
    one = FanDraft(f"f:{key}", [net], drivers, legs)
    env.lanes.extend(deal(one, throughs, env.elems, "c:", env.apart))
    one.drivers = [replace(a, net=net) for a in one.drivers]  # each attach carries its net
    one.legs = [replace(a, net=net) for a in one.legs]
    parts.setdefault(key, []).append((bundle.pole if bundle else 0, net, one))
    return True


def _merged(key: str, parts: Sequence[tuple[int, str, FanDraft]], *, one_side: bool) -> FanDraft:
    """One fan from its nets: hub by net id; nets, drivers and legs by lane index then net id.

    The caller's poles may skip an index; the fan has one lane per pole in use (BUNDLE).
    """
    # nets[j] is the net of lane j: the lane lines and drops name their nets by it.
    by_id = sorted(parts, key=lambda p: natural_key(p[1]))
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


def cross_link(net: str, ends: Sequence[NetEnd], lanes: Sequence[LaneDraft]) -> CrossLink:
    """The net as a wire between its ends: a lane cell, or a box pin."""
    where = {
        c.sym: (lane.column, lane.index, i) for lane in lanes for i, c in enumerate(lane.cells)
    }
    out = []
    for e in ends:
        col, lane_index, cell = where.get(e.pin.sym, (None, 0, 0))
        out.append(
            resolve(Att(None, "boxpin", e.pin, net=net))
            if col is None
            else Attach(col, lane_index, cell, e.pin, net=net)
        )
    return CrossLink(net, tuple(out))
