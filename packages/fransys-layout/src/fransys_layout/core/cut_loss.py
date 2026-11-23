"""What a loss withdraws from the drawn conductors, and the plan the loop asks again from what stands (ACCOUNT-IN-PLAN, R3430)."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from .cut_ledger import stand_class
from .cut_pieces import fan_pins
from .flow_values import block_id
from .values import PinRef, Ref, RefEnd, RefKind, StandClass

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .flow_values import Attach, Fan
    from .outputs import Refused
    from .values import PagePlan

__all__ = ("arrowed", "restood", "whole", "withdrawn")

type Pair = tuple[PinRef, PinRef]


def _rides(u: PinRef, v: PinRef, fan_of: Mapping[PinRef, AbstractSet[PinRef]], ink: Collection[Pair]) -> bool:
    """The conductor from fan pin `u` to `v` rides `u`'s leg: `v` is on its fan, or no wire draws it (it rides an arrow, copy or stub)."""
    return u in fan_of and (v in fan_of[u] or (u, v) not in ink)


def withdrawn(lost: Iterable[Refused], far_ends: Iterable[Pair], ink: Collection[Pair], fans: Iterable[Fan]) -> frozenset[Pair]:
    """The conductors the losses withdraw, both directions: a pair inside one loss, and the pairs a lost fan pin's leg carried.

    The router withholds a lost pin's leg (`route_trunk._withheld`), so the pairs that leg carried go; an ink pair to a pin off the fan
    has a wire of its own and stays. This is the one home of what a loss joins; the router decides only which pins it withheld.
    """
    pins = [frozenset(r.ends) for r in lost if r.ends]
    fan_of = fan_pins(fans)
    return frozenset(
        (a, b) for a, b in far_ends for p in pins if (a in p and (b in p or _rides(a, b, fan_of, ink))) or (b in p and _rides(b, a, fan_of, ink))
    )


def _reach(pairs: Iterable[Pair], ink: Collection[Pair], down: AbstractSet[PinRef]) -> list[PinRef]:
    """The far pins a loss names at one pin: its withdrawn ink partners, and its arrow riders when no partner stays live (Q6 b)."""
    partners = [far for near, far in pairs if (near, far) in ink]
    riders = [far for near, far in pairs if (near, far) not in ink]
    return partners + (riders if all(far in down for far in partners) else [])


def _grown(r: Refused, held: Mapping[PinRef, list[Pair]], ink: Collection[Pair], down: AbstractSet[PinRef]) -> Refused:
    """`r` with the far pins `held` names at each of its pins."""
    pins = r.ends or ()
    return replace(r, ends=tuple(dict.fromkeys((*pins, *(far for p in pins for far in _reach(held.get(p, ()), ink, down))))))


def whole(
    lost: Iterable[Refused], far_ends: Iterable[Pair], ink: Collection[Pair], gone: tuple[AbstractSet[Pair], AbstractSet[str]], fans: Iterable[Fan]
) -> tuple[tuple[Refused, ...], dict[PinRef, str]]:
    """Each loss that withdraws a conductor, with the placed far pin of every conductor `gone[0]` takes from one of its pins: both sides are marked.

    Also the pins the loop withholds, with their nets: the lost pins, and each fan pin a group names over no wire whose fan conductors all go.
    `gone[1]` are the symbols on a page. A lone pin that withdraws nothing gets no group (R3430 Q2).
    """
    pairs, placed = gone
    held: dict[PinRef, list[Pair]] = {}
    for near, far in (pair for pair in far_ends if pair in pairs):
        held.setdefault(near, []).extend([(near, far)] * (far.sym in placed))
    lost = list(lost)
    named = [r for r in lost if len(r.ends or ()) > 1 or any(p in held for p in r.ends or ())]
    down = {p for r in named for p in r.ends or ()}
    groups = tuple(_grown(r, held, ink, down) for r in named)
    fan_of = fan_pins(fans)
    withheld = {p: r.net for r in lost for p in r.ends or ()}
    spent = {
        x: g.net
        for g in groups
        for x in g.ends or ()
        if x not in withheld
        and x in fan_of
        and not any((p, x) in ink for p in g.ends or ())
        and all((x, y) in pairs for a, y in far_ends if a == x and y in fan_of[x])
    }
    return groups, withheld | spent


def _end(
    end: RefEnd, kept: Mapping[PinRef, int], down: AbstractSet[PinRef], gone: AbstractSet[Pair], named: AbstractSet[Pair] | None
) -> list[RefEnd]:
    """`end` asked again where it stands, from the ink its pins keep: each withheld pin of a bundle end alone, the pins that stand together.

    A pin-stood end holds no column or row. A stub end (`named` given) drops each far pin a group already names, and goes when that leaves
    it no conductor to name (R2766 D).
    """
    pins = (end.pin, *end.also)
    if end.pin is None or not end.also or not any(p in down for p in pins):
        parts = [end]
    else:
        live, dead = [p for p in pins if p not in down], [p for p in pins if p in down]
        parts = (
            [replace(end, pin=live[0], also=tuple(live[1:]), far=tuple(f for f in end.far if not any((d, f) in gone for d in dead)))] if live else []
        )
        parts += [replace(end, pin=d, also=(), far=tuple(f for f in end.far if (d, f) in gone)) for d in dead]
    out = []
    for part in parts:
        stand = stand_class(kept[part.pin]) if part.pin is not None and part.pin in down and part.stand is not StandClass.PIN else None
        at = part if stand is None else replace(part, column=None, row=None, stand=stand) if stand is StandClass.PIN else replace(part, stand=stand)
        far = at.far if named is None else tuple(f for f in at.far if not any((p, f) in named for p in (at.pin, *at.also)))
        if far or not at.far or named is None:
            out.append(replace(at, far=far))
    return out


def _poles(fan: Fan) -> dict[PinRef, int]:
    """The lane each pin of `fan` stands in (one lane when the fan is not a bundle)."""
    return {a.pin: a.pole if fan.lanes > 1 else 0 for a in (*fan.drivers, *fan.legs)}


def _dead(fan: Fan, arrows: Sequence[Ref], piece_of: Mapping[str, tuple[int, int]], down: AbstractSet[PinRef]) -> set[tuple[int, int]]:
    """The (arrow, pole) pairs that die: a lane on one trunk with no standing pin and at most one arrow end there, to a fixed point.

    A lane between two arrow ends relays and stays (the KI-1122 witness).
    """
    pole = _poles(fan)
    standing: Counter[tuple[tuple[int, int | None], int]] = Counter(
        (piece_of[_key(a)], pole[a.pin]) for a in (*fan.drivers, *fan.legs) if a.pin not in down and _key(a) in piece_of
    )
    ends = [(i, (e.page, e.row)) for i, r in enumerate(arrows) for e in r.ends[:2]]
    alive = {(i, pole.get(p, 0)) for i, r in enumerate(arrows) for e in r.ends[:2] for p in (e.pin, *e.also)}
    every, sites = set(alive), {(at, k) for i, at in ends for j, k in alive if j == i}
    while True:
        dead = set()
        for at, k in sites:
            touching = {i for i, there in ends if there == at and (i, k) in alive}
            if not standing[at, k] and len(touching) <= 1:
                dead |= {(i, k) for i in touching}
        if not dead:
            return every - alive
        alive -= dead


def _key(a: Attach) -> str:
    """The key of the column or block an attach stands in."""
    return a.column if a.column is not None else block_id("card", a.pin.sym)


def arrowed(plan: Iterable[Ref], fans: Iterable[Fan], pages: Sequence[PagePlan], down: AbstractSet[PinRef]) -> list[Ref]:
    """`plan` with each arrow end keeping the poles whose lane still stands on its trunk; an arrow with an end left empty goes (R3551).

    An arrow whose page has no pin left is a reference to nothing: its lane and lead go with the withheld pin (R3430 Q3, amended).
    """
    piece_of = {k: (pl.page, r) for pl in pages for r, row in enumerate(pl.rows) for k in (*row.columns, *row.blocks)}
    out = list(plan)
    for f in fans:
        idx = [i for i, r in enumerate(out) if r.kind is RefKind.ARROW and r.net == f.id]
        if not idx or not any(a.pin in down for a in (*f.drivers, *f.legs)):
            continue
        pole = _poles(f)
        dead = _dead(f, [out[i] for i in idx], piece_of, down)
        for n, i in enumerate(idx):
            ends = [
                replace(e, pin=keep[0], also=tuple(keep[1:]))
                for e in out[i].ends
                if (keep := [p for p in (e.pin, *e.also) if (n, pole.get(p, 0)) not in dead])
            ]
            out[i] = replace(out[i], ends=tuple(ends) if len(ends) == len(out[i].ends) else ())
    return out


def restood(
    plan: Iterable[Ref], down: AbstractSet[PinRef], groups: Iterable[Refused], gone: AbstractSet[Pair], ink: Collection[Pair]
) -> tuple[Ref, ...]:
    """`plan` with each stub, copy or star end at a withheld pin asked again where it stands, from the ink less `gone` (CL2).

    A stub end drops each far pin a group in `groups` already names, so a conductor a loss carries is named once (R2766 D).
    """
    kept = Counter(near for near, far in ink if (near, far) not in gone)
    named = {(a, b) for r in groups for a in r.ends or () for b in r.ends or () if a != b}
    out: list[Ref] = []
    for r in plan:
        again = r.kind in (RefKind.STUB, RefKind.COPY, RefKind.STAR)
        ends = tuple(x for e in r.ends for x in _end(e, kept, down, gone, named if r.kind is RefKind.STUB else None)) if again else r.ends
        if ends or not r.ends:
            out.append(replace(r, ends=ends))
    return tuple(out)
