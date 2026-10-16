"""Stage 1, part 5: leftover nets become attachments, fans (one per bundle) or cross-links."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .keys import natural_key
from .topology_fans import Att, FanDraft, LaneDraft, Slot, attached_pin, classify, deal, resolve
from .values import Attach, CrossLink, Fan, PinRef

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .topology_chains import Link
    from .topology_elements import Elem, NetEnd
    from .values import Bundle, Sym

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
            lane, where = env.slot[
                next((e.elem or "", e.pin.pin) for e in ends if e.site != "boxpin")
            ]
            attached[(lane.column, lane.index, where)] = pin
        elif not _fan_net(net, ends, parts, env):
            cross.append((net, [e for e in ends if e.site != "through"]))
    ordered = sorted(parts.items(), key=lambda kv: natural_key(kv[0]))
    fans = tuple(_fan(_merged(key, items)) for key, items in ordered)
    return fans, tuple(_cross(net, ends, env.lanes) for net, ends in cross), attached


def _fan_net(net: str, ends: tuple[NetEnd, ...], parts: Parts, env: FanEnv) -> bool:
    """Deal one net into its fan with its pole (a bundle shares one fan); False: a cross-link."""
    drivers, legs, throughs, is_cross = classify(ends, env.slot, env.syms)
    if is_cross or len(drivers) + len(legs) + len(throughs) < MIN_ATTS:
        return False
    bundle = env.bundle_of.get(net)
    key = bundle.id if bundle else net
    one = FanDraft(f"f:{key}", [net], drivers, legs)
    env.lanes.extend(deal(one, throughs, env.elems, "c:"))
    parts.setdefault(key, []).append((bundle.pole if bundle else 0, net, one))
    return True


def _merged(key: str, parts: Sequence[tuple[int, str, FanDraft]]) -> FanDraft:
    """One fan from its nets: nets and hub by net id, drivers and legs by pole then net id."""
    by_id = sorted(parts, key=lambda p: natural_key(p[1]))
    by_pole = sorted(by_id, key=lambda p: p[0])
    drivers = [a for _, _, one in by_pole for a in one.drivers]
    legs = [a for _, _, one in by_pole for a in one.legs]
    hub = next((one.hub for _, _, one in by_id if one.hub), None)
    nets = [net for _, net, _ in by_id]
    return FanDraft(f"f:{key}", nets, drivers, legs, hub, max(pole for pole, _, _ in parts) + 1)


def _fan(d: FanDraft) -> Fan:
    """The trunk lies above the legs; a fan whose only leg is a hub under a driver lies below."""
    side = "above" if any(a.where in ("head", "after-hub", "boxpin") for a in d.legs) else "below"
    drivers = tuple(resolve(a) for a in d.drivers)
    legs = tuple(resolve(a) for a in d.legs)
    return Fan(d.id, tuple(d.nets), drivers, legs, d.hub, d.lanes, side)


def _cross(net: str, ends: Sequence[NetEnd], lanes: Sequence[LaneDraft]) -> CrossLink:
    where = {
        c.sym: (lane.column, lane.index, i) for lane in lanes for i, c in enumerate(lane.cells)
    }
    out = []
    for e in ends:
        col, lane_index, cell = where.get(e.pin.sym, (None, 0, 0))
        out.append(
            resolve(Att(None, "boxpin", e.pin))
            if col is None
            else Attach(col, lane_index, cell, e.pin)
        )
    return CrossLink(net, tuple(out))
