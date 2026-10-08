"""Chain discovery, walk phase: the chains, their direction, and the bundles (chains.py)."""

from collections import Counter, defaultdict
from operator import itemgetter
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Set as AbstractSet

from fransys_layout.conventions import FACTS
from fransys_layout.geometry import follow

from ._chain_sides import _wired
from ._chain_state import _LINK_PORTS, _Links, _Reading, _Synthetic, _Walks
from ._chain_ties import _strip_of, needs_reverse
from .lookups import group_of
from .terminal_facts import TerminalRead

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from ._chain_state import _Nets, _Pole, _PoleId, _Poles, _Sides
    from .types import Connection, FunctionSpec, Handle


def _lone_end(
    port: Handle,
    nets: _Nets,
    state: _Poles,
    specs: Mapping[Handle, FunctionSpec],
    connections: tuple[Connection, ...],
) -> bool:
    """S13: `port`'s net holds one other port, of a terminal with no other wire."""
    net = nets.members[nets.net_of[port]]
    if len(net) != _LINK_PORTS:
        return False
    function = state.port_function[net[0] if net[1] == port else net[1]]
    wires = sum(1 for c in connections if function in (c.a.function, c.b.function))
    read = TerminalRead(specs[function].roles.terminal, len(specs[function].ports), wires)
    return bool(FACTS["terminal_point"].func(read))


def find_links(
    state: _Poles,
    nets: _Nets,
    specs: Mapping[Handle, FunctionSpec],
    connections: tuple[Connection, ...],
) -> _Links:
    """The links the chains follow."""
    # S13: a changeover whose two throws each end at a lone terminal hangs both under its pole
    # (`_attach`), so its chain no longer continues into the terminal at its throw on the pole
    detached = {
        on
        for on, off in state.throw_pairs
        if _lone_end(on, nets, state, specs, connections)
        and _lone_end(off, nets, state, specs, connections)
    }
    return _Links(
        members=nets.members,
        net_of=nets.net_of,
        pole_of_port=state.pole_of_port,
        detached=detached,
        connections=connections,
    )


def _turn_around(
    seq: Sequence[tuple[_PoleId, Handle, Handle]],
) -> list[tuple[_PoleId, Handle, Handle]]:
    """`seq` walked the other way: each step's entry and exit swap."""
    return [(p, x, e) for p, e, x in reversed(seq)]


def _across(
    port: Handle, poles: Mapping[_PoleId, _Pole], links: _Links
) -> tuple[_PoleId, Handle, Handle] | None:
    """The step `(pole, entry, exit)` across the link at `port`, or None at the chain's end."""
    q = links.partner(port)
    if q is None:
        return None
    pid = links.pole_of_port[q]
    ends = poles[pid].ports
    return pid, q, ends[1] if ends[0] == q else ends[0]


def _chain_start(
    pid: _PoleId, poles: Mapping[_PoleId, _Pole], links: _Links
) -> tuple[_PoleId, Handle]:
    """Back up from pole `pid` to the start of its chain: that pole and its entry port."""
    first = (pid, None, poles[pid].ports[0])
    start, _, port = follow(first, lambda s: _across(s[2], poles, links), key=itemgetter(0))[-1]
    return start, port


def _walk_forward(
    start: _PoleId, entry: Handle, poles: Mapping[_PoleId, _Pole], links: _Links
) -> tuple[list[tuple[_PoleId, Handle, Handle]], set[_PoleId]]:
    """The steps `(pole, entry, exit)` of the chain from `start`, and the poles it walked."""
    ends = poles[start].ports
    first = (start, entry, ends[1] if ends[0] == entry else ends[0])
    seq = follow(first, lambda s: _across(s[2], poles, links), key=itemgetter(0))
    return seq, {s[0] for s in seq}


def _vote_direction(
    seq: Sequence[tuple[_PoleId, Handle, Handle]], poles: Mapping[_PoleId, _Pole]
) -> tuple[Sequence[tuple[_PoleId, Handle, Handle]], bool]:
    """C4: only non-terminal poles vote on the direction; `seq` runs with the majority."""
    voters = [(p, e) for p, e, _ in seq if poles[p].inn is not None and not poles[p].terminal]
    forward = sum(1 for p, e in voters if poles[p].inn == e)
    backward = len(voters) - forward
    if backward > forward:
        seq = _turn_around(seq)
    return seq, forward != backward  # D1: a tie is decided as a direction-free chain


def _walk_all(
    poles: Mapping[_PoleId, _Pole], links: _Links, specs: Mapping[Handle, FunctionSpec]
) -> list[tuple[Sequence[tuple[_PoleId, Handle, Handle]], bool]]:
    """Every chain as `(steps, directed)`, in pole order."""
    seen: set[_PoleId] = set()
    walks: list[tuple[Sequence[tuple[_PoleId, Handle, Handle]], bool]] = []
    for pid in sorted(poles, key=lambda k: (specs[poles[k].function].key, str(poles[k].index))):
        if pid in seen:
            continue
        start, port = _chain_start(pid, poles, links)
        seq, walked = _walk_forward(start, port, poles, links)
        seen.update(walked)
        walks.append(_vote_direction(seq, poles))
    return walks


def _strip_entries(
    walks: Sequence[tuple[Sequence[tuple[_PoleId, Handle, Handle]], bool]], rd: _Reading
) -> dict[str, str | None]:
    """B9: a strip a directed chain passes through is entered by one terminal side (`PortRole`)."""
    # A chain that no pole votes on is entered by the same side; only with no such strip
    # does A6 decide.
    strip_entry: dict[str, str | None] = {}
    for seq, directed in walks:
        if directed:
            for p, e, _ in seq:
                if _strip_of(rd.poles[p], rd.specs):
                    strip_entry.setdefault(_strip_of(rd.poles[p], rd.specs), rd.port_side.get(e))
    return strip_entry


def _note_turns(
    seq: Sequence[tuple[_PoleId, Handle, Handle]], poles: Mapping[_PoleId, _Pole], out: _Walks
) -> None:
    """R6 D3: a terminal's entry port faces N; drawn at R180 when it is the S-facing one."""
    # D1: so is a non-terminal function whose directed poles all point against their chains
    # (a mate pole has no `inn`); the turn is per function, so a pole that points with its
    # chain vetoes it
    for p, e, _ in seq:
        pole = poles[p]
        if pole.inn is None:
            continue
        if pole.terminal:
            if pole.inn != e:
                out.flipped.add(pole.function)
        elif pole.inn == e:
            out.along.add(pole.function)
        else:
            out.against.add(pole.function)


def _note_edges(seq: Sequence[tuple[_PoleId, Handle, Handle]], rd: _Reading, out: _Walks) -> None:
    """D8: the direction is final here; a cross-unit mate stands at an end of its column."""
    # The chain enters its edge pole at the stand-in port (from the unit edge) at a top end,
    # and the parent-side pin is drawn turned (R180) so its wire port faces S into the column
    for p, e, _ in seq:
        if p in rd.edge_poles and e == rd.poles[p].ports[1]:
            out.edge_top.add(p)
            out.flipped.add(rd.poles[p].functions[0])


def _note_upper(
    seq: Sequence[tuple[_PoleId, Handle, Handle]], poles: Mapping[_PoleId, _Pole], out: _Walks
) -> None:
    """R7 A (designer, amends J3 inside a chain): the pin the chain enters first is on top."""
    # A pair in no chain keeps the J3 order
    if len(seq) > 1:
        for p, e, _ in seq:
            if poles[p].kind is _Synthetic.MATE:
                out.upper_of[p] = poles[p].functions[poles[p].ports.index(e)]


def _split_at_groups(
    seq: Sequence[tuple[_PoleId, Handle, Handle]],
    poles: Mapping[_PoleId, _Pole],
    specs: Mapping[Handle, FunctionSpec],
    wires_of: Callable[[_Pole], int],
) -> list[Sequence[tuple[_PoleId, Handle, Handle]]]:
    """C7: `seq` cut where the group of one pole's function differs from the next one's."""
    # A chain splits when the upstream side holds a function before the change (a terminal
    # heading a chain has no upstream part); a terminal at the change ends the upstream piece,
    # and its replica heads the downstream one (replicate_terminals, B8)
    pieces, start = [], 0
    for i in range(len(seq) - 1):
        here, there = (group_of(specs[poles[seq[j][0]].function]) for j in (i, i + 1))
        if here == there:
            continue
        if poles[seq[i][0]].terminal and i == start:
            continue  # a terminal heading its piece has no upstream part
        last = poles[seq[i + 1][0]]
        end = i + 1 == len(seq) - 1  # `wires_of` is read only at the chain's end
        if end and FACTS["terminal_point"].func(
            TerminalRead(last.terminal, len(last.ports), wires_of(last))
        ):
            continue  # nor has a one-wire terminal ending the chain a downstream part
        pieces.append(seq[start : i + 1])
        start = i + 1
    pieces.append(seq[start:])
    return pieces


def _settle_walk(
    walk: tuple[Sequence[tuple[_PoleId, Handle, Handle]], bool],
    rd: _Reading,
    links: _Links,
    out: _Walks,
) -> None:
    """Fix one walk's direction, note its turns, and add its pieces to the chains."""
    seq, directed = walk
    if not directed and len(seq) > 1 and needs_reverse(seq, rd):
        seq = _turn_around(seq)
    _note_turns(seq, rd.poles, out)
    _note_edges(seq, rd, out)
    _note_upper(seq, rd.poles, out)
    for piece in _split_at_groups(seq, rd.poles, rd.specs, links.wires_on):
        out.chains.append([p for p, _, _ in piece])
        out.ends_of[tuple(out.chains[-1])] = (piece[0][1], piece[-1][2])


def _reading(
    state: _Poles,
    specs: Mapping[Handle, FunctionSpec],
    rank_of: Mapping[Handle, int],
    tie_key: Mapping[Handle, tuple[str, ...]],
) -> _Reading:
    """The direction pass's inputs; `strip_entry` is filled once the walks are known."""
    return _Reading(
        poles=state.poles,
        edge_poles=state.edge_poles,
        port_function=state.port_function,
        specs=specs,
        rank_of=rank_of,
        tie_key=tie_key,
        port_side={p.port: p.strip_side for spec in specs.values() for p in spec.ports},
        strip_entry={},
    )


def walk_chains(
    state: _Poles,
    links: _Links,
    specs: Mapping[Handle, FunctionSpec],
    rank_of: Mapping[Handle, int],
    tie_key: Mapping[Handle, tuple[str, ...]],
) -> _Walks:
    """Walk every chain, settle its direction, and record the turns D1 and D3 ask for."""
    walks = _walk_all(state.poles, links, specs)
    rd = _reading(state, specs, rank_of, tie_key)
    rd.strip_entry.update(_strip_entries(walks, rd))
    out = _Walks()
    for walk in walks:
        _settle_walk(walk, rd, links, out)
    out.turned = out.against - out.along  # D1: only these are drawn MR180
    out.flipped |= out.turned
    return out


def _spare(
    chain: Sequence[_PoleId],
    longer: AbstractSet[Handle],
    state: _Poles,
    nets: _Nets,
    side_ports: Mapping[_PoleId, set[Handle]],
) -> bool:
    """Whether the one-pole `chain` is an unwired pole of a function that stands elsewhere."""
    (pid,) = chain
    pole = state.poles[pid]
    return (
        not pole.terminal
        and pole.function in longer
        and not _wired(
            pole.ports, (*pole.ports, *side_ports.get(pid, ())), nets.net_of, nets.net_size
        )
    )


def drop_unwired_poles(walks: _Walks, state: _Poles, nets: _Nets, found: _Sides) -> None:
    """D2: drop the one-pole chains of a function's unwired poles from `walks.chains`."""
    # Only a function with another pole in a longer chain, or one that is a side element of a
    # pole (`found.side_info`, D1 layout-0060), loses them. A contactor with only pole 1 wired
    # stands in that pole's column; its unwired poles open no column of their own, which would
    # claim the function away from the wired chain. A pole is unwired when no port outside its
    # group shares its nets: the group is the pole's two ports and the ports of its side poles
    # (`found.side_ports`, the ports they hid, D1), so a strap to a side pole does not wire it,
    # but a wire to a terminal, or to a function that is a side element nowhere, does.
    chains = walks.chains
    longer = {state.poles[p].function for ch in chains if len(ch) > 1 for p in ch}
    longer |= set(found.side_info)
    walks.chains = [
        ch for ch in chains if len(ch) > 1 or not _spare(ch, longer, state, nets, found.side_ports)
    ]


def _signature(
    chain: Sequence[_PoleId],
    poles: Mapping[_PoleId, _Pole],
    ends_of: Mapping[tuple[_PoleId, ...], tuple[Handle, Handle]],
    detached: AbstractSet[Handle],
) -> tuple[Any, ...]:
    """A chain's `(item, kind)` sequence, every terminal alike."""
    own = tuple(
        ()
        if poles[p].terminal and poles[p].kind is not _Synthetic.MATE
        else (poles[p].item, poles[p].kind)
        for p in chain
    )
    # S13: a chain bundles as it did while its detached throw's terminal stood at its end
    entry, exit_port = ends_of[tuple(chain)]
    head = ((),) if entry in detached else ()
    return head + own + (((),) if exit_port in detached else ())


def _pole_order(
    chain: Sequence[_PoleId],
    poles: Mapping[_PoleId, _Pole],
    specs: Mapping[Handle, FunctionSpec],
    key_order: Mapping[Handle, tuple[Any, ...]],
) -> tuple[Any, ...]:
    """A bundle's chains left to right: by the pole index of the first multi-pole function."""
    for p in chain:
        pole = poles[p]
        if (
            not pole.terminal
            and isinstance(pole.index, int)
            and len(specs[pole.function].pole_pairs) > 1
        ):
            return (0, pole.index)
    first = specs[poles[chain[0]].function]
    return (1, key_order.get(first.function, ()), first.key)  # layout-0165: 2 before 10


def _group_bundles(
    by_sig: Mapping[tuple[Any, ...], list[list[_PoleId]]],
    per_item: Mapping[Any, int],
    poles: Mapping[_PoleId, _Pole],
    specs: Mapping[Handle, FunctionSpec],
    key_order: Mapping[Handle, tuple[Any, ...]],
) -> list[list[list[_PoleId]]]:
    """Chains of one signature through an `(item, kind)` with several poles make one bundle."""
    bundles: list[list[list[_PoleId]]] = []
    for sig, group in by_sig.items():
        multi = any(len(k) == 2 and per_item[k] > 1 for k in sig)  # noqa: PLR2004 -- the count is the rule's own size (a pair or triple), not a tunable
        if len(group) > 1 and multi:
            bundles.append(
                sorted(group, key=lambda chain: _pole_order(chain, poles, specs, key_order))
            )
        else:
            bundles.extend([chain] for chain in group)
    return bundles


def bundle_chains(
    walks: _Walks,
    state: _Poles,
    links: _Links,
    specs: Mapping[Handle, FunctionSpec],
    key_order: Mapping[Handle, tuple[Any, ...]],
) -> None:
    """Fill `walks.bundles`: chains with one signature, one column each."""
    poles = state.poles
    per_item = Counter((pole.item, pole.kind) for pole in poles.values())
    by_sig: dict[tuple[Any, ...], list[list[_PoleId]]] = defaultdict(list)
    for chain in walks.chains:
        by_sig[_signature(chain, poles, walks.ends_of, links.detached)].append(chain)
    walks.bundles = _group_bundles(by_sig, per_item, poles, specs, key_order)
