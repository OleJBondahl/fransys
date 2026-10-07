"""Chain discovery, reach phase: which column a non-series function joins (chains.py)."""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_layout.conventions import FACTS
from fransys_layout.geometry import follow

from ._chain_state import _Group, _Reach
from .terminal_facts import TerminalRead

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import AuthoringKey

    from ._chain_state import _Nets, _PoleId, _Poles, _Walks
    from .types import Connection, DrawnFunction, FunctionSpec, Handle


def start_reach(
    state: _Poles,
    nets: _Nets,
    specs: Mapping[Handle, FunctionSpec],
    drawn_of: Mapping[Handle, DrawnFunction],
    side_info: Mapping[Handle, tuple[bool, bool]],
) -> _Reach:
    """The reach state: the functions already in a pole."""
    # C1 (owner): a column continues through a non-series function its end nets reach;
    # C1b claim by most ports; C1c no flip above two ports; (iii) single chains ending on one
    # multi-port function are adjacent lanes with it spanning under them; same location only
    in_poles = {
        f
        for pid, pole in state.poles.items()
        for f in (pole.functions[:1] if pid in state.edge_poles else pole.functions)
    } | set(side_info)  # an edge pin is still reached at home, in its own unit's chain
    return _Reach(state=state, nets=nets, specs=specs, drawn_of=drawn_of, in_poles=in_poles)


def _symbol_of(drawn: DrawnFunction) -> dict[Handle, str]:
    return {dp.port: dp.symbol_port for dp in drawn.ports}


def _facing(drawn: DrawnFunction, port: Handle) -> str | None:
    faces = {g.name: g.facing.value for g in drawn.geometry.ports}
    return faces.get(_symbol_of(drawn).get(port))


def _home(r: _Reach, b: int) -> int:
    """The group `b` was merged into, or `b`."""
    return follow(b, r.alias.get)[-1]


def _reach_of(r: _Reach, port: Handle) -> tuple[Handle, Handle] | None:
    """The function, and its port, the net of `port` joins `port` to alone."""
    others = [q for q in r.nets.members[r.nets.net_of[port]] if q != port]
    if len(others) != 1 or others[0] not in r.state.port_function:
        return None
    function = r.state.port_function[others[0]]
    if function in r.in_poles or function not in r.drawn_of or r.specs[function].roles.terminal:
        return None
    return function, others[0]


def _lone_terminal(
    r: _Reach, bundle: Sequence[list[_PoleId]], connections: tuple[Connection, ...]
) -> bool:
    """C9: a bundle of one terminal pole with one wire attaches by L9, beside neighbours."""
    pole = r.state.poles[bundle[0][0]]
    if len(bundle) != 1 or len(bundle[0]) != 1 or not pole.terminal:  # cost gate, not the rule
        return False
    ports = set(pole.ports)
    wires = sum(1 for c in connections if c.a.port in ports or c.b.port in ports)
    return bool(FACTS["terminal_point"].func(TerminalRead(pole.terminal, len(ports), wires)))


def _vote_lane(
    r: _Reach, b: int, lane_of: int, ends: tuple[Handle, Handle], top: FunctionSpec
) -> None:
    """Vote for the functions the two ends of one lane reach, in `top`'s location."""
    entry, exit_port = ends
    for port, at_exit in ((exit_port, True), (entry, False)):
        hit = _reach_of(r, port)
        if hit is None or r.specs[hit[0]].location_path != top.location_path:
            continue
        # V1: a pin whose side is fixed has its part on that side: below an N pin, above an S
        below = _facing(r.drawn_of[hit[0]], hit[1]) == "n" if hit[1] in r.fixed else at_exit
        r.votes[hit[0]].setdefault(b, []).append((hit[1], below))
        r.lane_hit.setdefault((hit[0], b), lane_of)
        r.span_hit.setdefault((hit[0], b), hit[1])


def _vote(
    r: _Reach,
    bundles: Sequence[list[list[_PoleId]]],
    ends_of: Mapping[tuple[_PoleId, ...], tuple[Handle, Handle]],
    connections: tuple[Connection, ...],
) -> None:
    """Every bundle's lane ends vote for the function they reach."""
    for b, bundle in enumerate(bundles):
        top = r.specs[r.state.poles[bundle[0][0]].function]
        if _lone_terminal(r, bundle, connections):
            continue
        for lane_of, chain in enumerate(bundle):
            _vote_lane(r, b, lane_of, ends_of[tuple(chain)], top)


def _rekey(r: _Reach, b: int, lead: int, offset: int) -> None:
    """Move the lane and span votes of group `b` to `lead`, its single chain now lane `offset`."""
    for (function, group), lane in list(r.lane_hit.items()):
        if group == b:
            r.lane_hit.setdefault((function, lead), lane + offset)
    for (function, group), port in list(r.span_hit.items()):
        if group == b:
            r.span_hit.setdefault((function, lead), port)


def _singles(r: _Reach, hits: Mapping[int, list[tuple[Handle, bool]]], *, below: bool) -> list[int]:
    """The groups of one chain whose ports all lie on the `below` side and have no extra."""
    return [
        b
        for b, found in hits.items()
        if len(r.groups[b].chains) == 1
        and all(down == below for _, down in found)
        and b not in r.extra
    ]


def _fold(
    r: _Reach, hits: Mapping[int, list[tuple[Handle, bool]]], singles: Sequence[int], *, below: bool
) -> dict[int, list[tuple[Handle, bool]]]:
    """`hits` with every group of `singles` merged into the first, which keeps chains and votes."""
    merged = dict(hits)
    lead = singles[0]
    for b in singles[1:]:
        _rekey(r, b, lead, len(r.groups[lead].chains))
        r.groups[lead].chains.extend(r.groups[b].chains)
        merged[lead].extend(merged.pop(b))
        r.alias[b] = lead
        del r.groups[b]
    r.groups[lead].bottom = below
    return merged


def _merge_singles(
    r: _Reach, function: Handle, hits: Mapping[int, list[tuple[Handle, bool]]]
) -> dict[int, list[tuple[Handle, bool]]]:
    """(iii): `hits` with the single chains that all end below on one multi-port function merged."""
    drawn = r.drawn_of[function]
    symbol = _symbol_of(drawn)
    port_x = {g.name: g.at.x for g in drawn.geometry.ports}
    # V1: on an item box whose pins V1 fixes, those that all end above merge too, on top
    below = not any(p in r.fixed and not down for found in hits.values() for p, down in found)
    singles = _singles(r, hits, below=below)
    if len(drawn.geometry.ports) > 2 and len(singles) > 1:  # noqa: PLR2004 -- (iii)
        singles.sort(key=lambda b: min(port_x.get(symbol.get(p), 0) for p, _ in hits[b]))
        return _fold(r, hits, singles, below=below)
    return dict(hits)


def _score(
    r: _Reach, hits: Mapping[int, list[tuple[Handle, bool]]], b: int
) -> tuple[int, str, AuthoringKey]:
    """C1b: the group with most ports wins, then the first by designation."""
    top = r.specs[r.state.poles[r.groups[b].chains[0][0]].function]
    return (-len(hits[b]), top.designation, top.key)


def _turn(
    r: _Reach, function: Handle, found: Sequence[tuple[Handle, bool]], *, below: bool
) -> bool:
    """C1c: whether a function of two ports turns: its port faces away from the column."""
    port = next(p for p, down in found if down == below)
    return _facing(r.drawn_of[function], port) == ("s" if below else "n")


def _claim(r: _Reach, function: Handle) -> bool:
    """The group `function` joins, above or below; whether it turns."""
    gathered: dict[int, list[tuple[Handle, bool]]] = defaultdict(list)
    for b, found in r.votes[function].items():
        gathered[_home(r, b)].extend(found)
    hits = _merge_singles(r, function, gathered)
    winner = min(hits, key=lambda b: _score(r, hits, b))
    reached = r.span_hit.get((function, winner))
    bound = _symbol_of(r.drawn_of[function])
    if reached in bound:
        r.span_symbol[function] = bound[reached]  # C12
    below = sum(1 for _, down in hits[winner] if down) >= sum(
        1 for _, down in hits[winner] if not down
    )
    r.extra[winner][1 if below else 0].append(function)
    return len(r.drawn_of[function].geometry.ports) <= 2 and _turn(  # noqa: PLR2004 -- C1c
        r, function, hits[winner], below=below
    )


def _star_first(
    r: _Reach, function: Handle, lane_of_pole: Mapping[_PoleId, tuple[int, int]]
) -> tuple[Handle, Handle] | None:
    """The star net's first member by designation that stands in a column, with the pin's port."""
    spec = r.specs[function]
    if (
        spec.pin_function is None
        or len(spec.ports) != 1
        or function not in r.drawn_of
        or function in r.in_poles
        or function in r.votes
    ):
        return None
    port = spec.ports[0].port
    net = r.nets.members.get(r.nets.net_of.get(port), [])
    state = r.state
    others = [
        q
        for q in net
        if q != port and q in state.pole_of_port and state.pole_of_port[q] in lane_of_pole
    ]
    if len(net) < 3 or not others:  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
        return None
    first = min(others, key=lambda q: (r.specs[state.port_function[q]].designation, q))
    return first, port


def _star_pin(r: _Reach, function: Handle, lane_of_pole: Mapping[_PoleId, tuple[int, int]]) -> bool:
    """Put a pin on a star net in the column of the star's first member; whether it flips."""
    found = _star_first(r, function, lane_of_pole)
    if found is None:
        return False
    first, port = found
    b, lane = lane_of_pole[r.state.pole_of_port[first]]
    b = _home(r, b)
    below = _facing(r.drawn_of[r.state.port_function[first]], first) == "s"
    r.extra[b][1 if below else 0].append(function)
    r.lane_hit.setdefault((function, b), lane)
    # it flips when its port does not face the member
    return _facing(r.drawn_of[function], port) != ("n" if below else "s")


def vote_columns(r: _Reach, walks: _Walks, connections: tuple[Connection, ...]) -> None:
    """Vote, claim, and place the pins of star nets; leaves `r.extra`, `r.groups` and the flips."""
    r.groups.update({b: _Group(list(bundle)) for b, bundle in enumerate(walks.bundles)})
    _vote(r, walks.bundles, walks.ends_of, connections)
    for function in sorted(r.votes, key=lambda f: r.specs[f].key):
        if _claim(r, function):
            walks.flipped.add(function)
    # I4 Q2 (designer): a pin whose only net is a star (three or more ports) joins the column
    # of the star's first member by designation, below it when that member's port faces S,
    # above it when N; that end is then a wire, the other members keep their markers
    lane_of_pole = {
        pid: (b, lane)
        for b, group in r.groups.items()
        for lane, chain in enumerate(group.chains)
        for pid in chain
    }
    for function in sorted(r.specs, key=lambda f: r.specs[f].key):
        if _star_pin(r, function, lane_of_pole):
            walks.flipped.add(function)
