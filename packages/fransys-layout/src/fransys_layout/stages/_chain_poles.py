"""Chain discovery, poles phase: the series poles, in-line terminals, mate and edge poles."""

from collections import defaultdict
from typing import TYPE_CHECKING

from fransys_layout.conventions import FACTS
from fransys_model.kernel import Id

from ._chain_state import _LINK_PORTS, _Pole, _Poles, _Synthetic
from .resolve import throw_port
from .terminal_facts import TerminalRead
from .types import EDGE_KIND

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.geometry import ThroughPath

    from .types import Connection, DrawnFunction, FunctionSpec, Handle, MatedFunctions


def build_poles(
    functions: tuple[FunctionSpec, ...],
    drawn_of: Mapping[Handle, DrawnFunction],
    connections: tuple[Connection, ...],
    mates: tuple[MatedFunctions, ...],
    edge_mates: tuple[MatedFunctions, ...],
) -> _Poles:
    """Every pole of the drawn `functions`, with the port maps the later phases read."""
    specs = {spec.function: spec for spec in functions}
    state = _Poles(
        poles={},
        pole_of_port={},
        port_function={p.port: s.function for s in functions for p in s.ports},
        split={},
        throw_pairs=[],
        edge_poles=set(),
    )
    for function, d in sorted(drawn_of.items()):
        spec = specs[function]
        _add_function_poles(state, spec, d, _pole_pairs(state, spec, d))
    _inline_terminal_poles(state, functions, drawn_of, connections)
    _mate_poles(state, specs, mates)
    _edge_mate_poles(state, specs, edge_mates)
    _off_stub_poles(state, specs, connections)
    return state


def _changeover_pairs(
    spec: FunctionSpec, d: DrawnFunction, through: ThroughPath
) -> tuple[list[tuple[int, str, str]], tuple[Handle, Handle] | None]:
    """I4: a changeover's pole pairs (its through path, NO to COM), and its throw pair if any."""
    # the NC port stays off the chain
    name_of = {dp.symbol_port: p.name for p in spec.ports for dp in d.ports if dp.port == p.port}
    if through.start not in name_of or through.end not in name_of:
        return [], None
    on = {through.start, through.end}
    throws = [p for p in spec.ports if p.throw in ("break", "make")]
    chained = [p.port for p in throws if throw_port(spec, p) in on]
    off = [p.port for p in throws if throw_port(spec, p) not in on]
    throw = (chained[0], off[0]) if len(chained) == len(off) == 1 else None
    return [(0, name_of[through.start], name_of[through.end])], throw


def _pole_pairs(state: _Poles, spec: FunctionSpec, d: DrawnFunction) -> list[tuple[int, str, str]]:
    """The `(index, first, second)` port names of a function's poles, else its through path's."""
    pairs = [(pp.index, pp.first, pp.second) for pp in spec.pole_pairs]
    if pairs or d.geometry.through is None:
        return pairs
    if len(spec.ports) == _LINK_PORTS:
        first, second = (p.name for p in spec.ports)
        return [(0, first, second)]
    pairs, throw = _changeover_pairs(spec, d, d.geometry.through)
    if throw is not None:
        state.throw_pairs.append(throw)
    return pairs


def _add_function_poles(
    state: _Poles, spec: FunctionSpec, d: DrawnFunction, pairs: Sequence[tuple[int, str, str]]
) -> None:
    """One pole per pair of a drawn function, `inn` its N-facing port when the other faces S."""
    by_name = {p.name: p.port for p in spec.ports}
    symbol_port = {dp.port: dp.symbol_port for dp in d.ports}
    facing = {g.name: g.facing.value for g in d.geometry.ports}
    for index, first, second in pairs:
        ends = (by_name[first], by_name[second])
        north = [p for p in ends if facing.get(symbol_port.get(p)) == "n"]
        south = [p for p in ends if facing.get(symbol_port.get(p)) == "s"]
        inn = north[0] if len(north) == 1 and len(south) == 1 else None
        pid = (spec.function, index)
        state.poles[pid] = _Pole(
            function=spec.function,
            functions=(spec.function,),
            index=index,
            ports=ends,
            inn=inn,
            item=spec.item,
            kind=d.kind,
            terminal=d.roles.terminal,
        )
        for p in ends:
            state.pole_of_port[p] = pid


def _inline_terminal_poles(
    state: _Poles,
    functions: tuple[FunctionSpec, ...],
    drawn_of: Mapping[Handle, DrawnFunction],
    connections: tuple[Connection, ...],
) -> None:
    """R7 B5: a one-port terminal with exactly two wires on its port is an in-line pole."""
    # the second wire (by conductor handle) enters it at a stand-in port, the conductor's own Id
    by_port: dict[Handle, list[Handle]] = defaultdict(list)
    for c in connections:
        for end in {c.a.port, c.b.port}:
            by_port[end].append(c.handle)
    for spec in sorted(functions, key=lambda s: s.key):
        ports = {p.port for p in spec.ports}
        wires = sorted({h for p in ports for h in by_port.get(p, ())})
        read = TerminalRead(spec.roles.terminal, len(ports), len(wires))
        if spec.function not in drawn_of or not FACTS["inline_terminal"].func(read):
            continue
        port = spec.ports[0].port
        state.split[wires[1]] = port
        state.port_function[wires[1]] = spec.function
        pid = (spec.function, 0)
        state.poles[pid] = _Pole(
            function=spec.function,
            functions=(spec.function,),
            index=0,
            ports=(port, wires[1]),
            inn=None,
            item=spec.item,
            kind=spec.kind,
            terminal=True,
        )
        state.pole_of_port[port] = state.pole_of_port[wires[1]] = pid


def _mate_poles(
    state: _Poles, specs: Mapping[Handle, FunctionSpec], mates: tuple[MatedFunctions, ...]
) -> None:
    """A mated pin pair (equal-named ports of two mated functions) is a direction-free pole."""
    for pair in mates:
        a, b = pair.a, pair.b
        if a not in specs or b not in specs:
            continue
        a_ports = {p.name: p.port for p in specs[a].ports}
        b_ports = {p.name: p.port for p in specs[b].ports}
        for name in sorted(a_ports.keys() & b_ports.keys()):
            pa, pb = a_ports[name], b_ports[name]
            if pa in state.pole_of_port or pb in state.pole_of_port:
                continue
            pid = (a, b, name)
            state.poles[pid] = _Pole(
                function=a,
                functions=(a, b),
                index=name,
                ports=(pa, pb),
                inn=None,
                item=(_Synthetic.MATE, specs[a].pin_function or a, specs[b].pin_function or b),
                kind=_Synthetic.MATE,
                terminal=True,
            )
            state.pole_of_port[pa] = state.pole_of_port[pb] = pid


def _edge_mate_poles(
    state: _Poles, specs: Mapping[Handle, FunctionSpec], edge_mates: tuple[MatedFunctions, ...]
) -> None:
    """A pin mated across a unit edge: a mate pole whose `b` end is a stand-in port on no net."""
    for pair in edge_mates:
        a, b = pair.a, pair.b
        if a not in specs or b not in specs or len(specs[a].ports) != 1:
            continue
        pa = specs[a].ports[0].port
        stand_in = Id(kind=EDGE_KIND, value=b.value)  # on no net: the chain stops at the edge
        if pa in state.pole_of_port:
            continue
        state.port_function[stand_in] = b
        pid = (a, b, "edge")
        state.poles[pid] = _Pole(
            function=a,
            functions=(a, b),
            index="edge",
            ports=(pa, stand_in),
            inn=None,
            item=(_Synthetic.MATE, specs[a].pin_function or a, specs[b].pin_function or b),
            kind=_Synthetic.MATE,
            terminal=True,
        )
        state.pole_of_port[pa] = state.pole_of_port[stand_in] = pid
        state.edge_poles.add(pid)


def _off_stub_poles(
    state: _Poles, specs: Mapping[Handle, FunctionSpec], connections: tuple[Connection, ...]
) -> None:
    """W3: a one-port pin whose conductor leaves at the edge is a pole from its port to the edge."""
    # (a unit's boundary pin carrying its outside mate's off-stub)
    for c in connections:
        for end, other in ((c.a, c.b), (c.b, c.a)):
            spec = specs.get(end.function)
            if other.function.kind != EDGE_KIND or spec is None or spec.pin_function is None:
                continue
            if end.port in state.pole_of_port:
                continue
            stand_in = Id(kind=EDGE_KIND, value=f"{other.port.value}-pole")  # on no net
            state.port_function[stand_in] = end.function
            pid = (end.function, other.function, "off")
            state.poles[pid] = _Pole(
                function=end.function,
                functions=(end.function,),
                index="off",
                ports=(end.port, stand_in),
                inn=None,
                item=(_Synthetic.OFF, spec.pin_function),
                kind=_Synthetic.PIN,
                terminal=False,
            )
            state.pole_of_port[end.port] = state.pole_of_port[stand_in] = pid
