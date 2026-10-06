"""Chain discovery, nets phase: the nets over the ports, and the side elements on them (D1)."""

from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from ._chain_state import _Nets, _Poles, _Sides
from .lookups import nets_from_pairs

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from ._chain_state import _Pole, _PoleId
    from .types import Connection, DrawnFunction, FunctionSpec, Handle, NetGroup

# Poles on the same two nets: one carrier and at least one side element make a group.
_SIDE_GROUP_MIN = 2


def _joins(
    state: _Poles, connections: tuple[Connection, ...], net_groups: tuple[NetGroup, ...]
) -> list[tuple[Handle, Handle]]:
    """The port pairs the conductors and the declared nets join."""
    joins: list[tuple[Handle, Handle]] = []
    for c in connections:
        if c.handle in state.split:  # R7 B5: the split terminal's second wire ends at its stand-in
            end = c.b.port if c.a.port == state.split[c.handle] else c.a.port
            joins.append((end, c.handle))
            continue
        joins.append((c.a.port, c.b.port))
    for g in net_groups:
        joins.extend((x.port, y.port) for x, y in zip(g.ports, g.ports[1:], strict=False))
    return joins


def build_nets(
    state: _Poles, connections: tuple[Connection, ...], net_groups: tuple[NetGroup, ...]
) -> _Nets:
    """The nets over the ports of these functions only, with each net's members and size."""
    joins = _joins(state, connections, net_groups)
    nets = nets_from_pairs(
        ((a, b) for a, b in joins if a in state.port_function and b in state.port_function),
        state.port_function,
    )
    net_of = {p: nets.find(p) for p in state.port_function}
    members: dict[Handle, list[Handle]] = defaultdict(list)
    for p in sorted(state.port_function):
        members[net_of[p]].append(p)
    return _Nets(net_of=net_of, members=members, net_size=Counter(net_of.values()))


def _wired(
    ports: tuple[Handle, ...],
    group: tuple[Handle, ...],
    net_of: Mapping[Handle, Handle],
    net_size: Mapping[Handle, int],
) -> bool:
    """D1: a pole on `ports` is wired when a port outside `group` shares the nets of its ports."""
    # `group` is the pole's two ports and the ports of its side poles (the ports they hid).
    return any(
        net_size[net_of[port]] - sum(1 for q in group if net_of[q] == net_of[port]) > 0
        for port in ports
    )


def _carried_by(
    picks: Sequence[tuple[_PoleId, list[_PoleId]]], poles: Mapping[_PoleId, _Pole]
) -> tuple[dict[Handle, set[Handle]], dict[_PoleId, set[Handle]]]:
    """The carrier functions of each side function, and the ports each carrier pole's picks hide."""
    carried_by: dict[Handle, set[Handle]] = defaultdict(set)
    side_ports: dict[_PoleId, set[Handle]] = defaultdict(set)
    for main, rest in picks:
        for pid in rest:
            side_ports[main].update(poles[pid].ports)
            if poles[pid].function != poles[main].function:
                carried_by[poles[pid].function].add(poles[main].function)
    return carried_by, side_ports


def _side_nowhere(
    picks: Sequence[tuple[_PoleId, list[_PoleId]]],
    poles: Mapping[_PoleId, _Pole],
    net_of: Mapping[Handle, Handle],
    net_size: Mapping[Handle, int],
) -> set[Handle]:
    """D1: the functions that are a side element nowhere, read from every pick at once."""
    # `picks` is each group's `(carrier pole, side poles)`. A function that carries another
    # function's pole, or that is a side element of more than one carrier function, or that has a
    # wired pole (`_wired`) that is no side pole, is one; a side pole of the carrier's own function
    # is no conflict. A pole's group here is its ports and those of the poles the picks make its
    # side poles.
    carried_by, side_ports = _carried_by(picks, poles)
    carriers = set().union(*carried_by.values())
    side_poles = {pid for _, rest in picks for pid in rest}
    live = {
        pole.function
        for pid, pole in poles.items()
        if pole.function in carried_by
        and not pole.terminal
        and pid not in side_poles
        and _wired(pole.ports, (*pole.ports, *side_ports.get(pid, ())), net_of, net_size)
    }
    return carriers | live | {f for f, by in carried_by.items() if len(by) > 1}


def _pole_rank(
    pid: _PoleId,
    group: Sequence[_PoleId],
    poles: Mapping[_PoleId, _Pole],
    specs: Mapping[Handle, FunctionSpec],
    tie_key: Mapping[Handle, tuple[str, ...]],
) -> tuple[bool, bool, str, tuple[str, ...], AuthoringKey, str]:
    """Carrier order of one group (lowest carries); D9: a coil before an element across it."""
    function = poles[pid].function
    child = any(
        specs[function].item_parent == specs[poles[o].function].item for o in group if o != pid
    )
    return (
        child,
        not specs[function].roles.coil,
        specs[function].designation,
        tie_key.get(function, ()),
        specs[function].key,
        str(poles[pid].index),
    )


def _picks(
    state: _Poles,
    nets: _Nets,
    specs: Mapping[Handle, FunctionSpec],
    tie_key: Mapping[Handle, tuple[str, ...]],
) -> list[tuple[_PoleId, list[_PoleId]]]:
    """Each group of non-terminal poles on the same two nets as `(carrier pole, side poles)`."""
    by_nets: dict[frozenset[Handle], list[_PoleId]] = defaultdict(list)
    for pid, pole in state.poles.items():
        if not pole.terminal:
            by_nets[frozenset(nets.net_of[p] for p in pole.ports)].append(pid)
    picks = []
    for group in by_nets.values():
        if len(group) < _SIDE_GROUP_MIN:
            continue
        main, *rest = sorted(
            group, key=lambda pid, g=group: _pole_rank(pid, g, state.poles, specs, tie_key)
        )
        picks.append((main, rest))
    return picks


def _add_side(state: _Poles, nets: _Nets, sides: _Sides, main: _PoleId, pid: _PoleId) -> None:
    """Record the function of pole `pid` as a side element of the carrier pole `main`."""
    side = state.poles[pid].function
    host_top = state.poles[main].inn
    sides.sides[main].append(side)
    sides.carrier_of[side] = state.poles[main].function
    own_top = state.poles[pid].inn
    flip = (
        host_top is not None
        and own_top is not None
        and nets.net_of[own_top] != nets.net_of[host_top]
    )
    sides.side_info[side] = (flip, False)


def _hide(state: _Poles, sides: _Sides, pid: _PoleId) -> None:
    """Hide the ports of side pole `pid` and drop it from the poles."""
    sides.hidden.update(state.poles[pid].ports)
    for p in state.poles[pid].ports:
        state.pole_of_port.pop(p, None)
    del state.poles[pid]


def _apply_picks(
    state: _Poles,
    nets: _Nets,
    sides: _Sides,
    picks: Sequence[tuple[_PoleId, list[_PoleId]]],
) -> None:
    """Fill `sides` from the picks; a side pole of the carrier's own function only hides."""
    nowhere = _side_nowhere(picks, state.poles, nets.net_of, nets.net_size)
    for main, rest in picks:
        for pid in rest:
            side = state.poles[pid].function
            own = side == state.poles[main].function
            if not own and side not in nowhere and side not in sides.sides[main]:
                _add_side(state, nets, sides, main, pid)
            if own or side not in nowhere:
                sides.side_ports[main].update(state.poles[pid].ports)
            _hide(state, sides, pid)


def _host_candidates(
    state: _Poles, nets: _Nets, specs: Mapping[Handle, FunctionSpec], port: Handle
) -> list[_PoleId]:
    """The poles on the net of `port`, a non-terminal pole first."""
    return sorted(
        {state.pole_of_port[p] for p in nets.members[nets.net_of[port]] if p in state.pole_of_port},
        key=lambda pid: (
            state.poles[pid].terminal,
            specs[state.poles[pid].function].key,
            str(pid[-1]),
        ),
    )


def _terminal_sides(
    state: _Poles,
    nets: _Nets,
    sides: _Sides,
    specs: Mapping[Handle, FunctionSpec],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> None:
    """A one-port terminal (a printed pass-through) is a side element of a pole on its net."""
    for spec in sorted(specs.values(), key=lambda s: s.key):
        if not spec.roles.terminal or len(spec.ports) != 1 or spec.function not in drawn_of:
            continue
        if (spec.function, 0) in state.poles:  # R7 B5: an in-line pole, not a side element
            continue
        port = spec.ports[0].port
        sides.hidden.add(port)
        candidates = _host_candidates(state, nets, specs, port)
        if candidates:
            host = state.poles[candidates[0]]
            sides.sides[candidates[0]].append(spec.function)
            sides.carrier_of[spec.function] = host.function
            low = host.inn is not None and nets.net_of[port] != nets.net_of[host.inn]
            sides.side_info[spec.function] = (False, low)


def find_sides(
    state: _Poles,
    nets: _Nets,
    specs: Mapping[Handle, FunctionSpec],
    tie_key: Mapping[Handle, tuple[str, ...]],
    drawn_of: Mapping[Handle, DrawnFunction],
) -> _Sides:
    """The side elements, hidden ports and carriers; `nets.members` loses the hidden ports."""
    # D1 (layout-0060): any two non-terminal poles on the same two nets, of one function or of
    # two, are one pole and its side elements. The carrier is the child-item rule's pick (a
    # suppressor's item is a child of its coil's), else the lower item designation (the
    # terminal list's key breaks a tie), then the function key and the pole index. A side pole
    # of the carrier's own function is drawn side by side in that one cell, so it only hides;
    # another function's is a side element cell. A function is a carrier or a side element,
    # never both, and the side element of one carrier function only: one that the picks make
    # both, or a side element of two carriers, is a side element nowhere (`_side_nowhere`, read
    # from all the picks at once). It keeps its own cell, its poles still hide their ports.
    sides = _Sides(
        sides=defaultdict(list),
        side_info={},
        carrier_of={},
        hidden=set(),
        side_ports=defaultdict(set),
    )
    _apply_picks(state, nets, sides, _picks(state, nets, specs, tie_key))
    _terminal_sides(state, nets, sides, specs, drawn_of)
    for root in nets.members:
        nets.members[root] = [p for p in nets.members[root] if p not in sides.hidden]
    return sides
