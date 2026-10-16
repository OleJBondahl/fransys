"""Stage 1, topology: build_flow(problem, options) -> FlowGraph, from pins, nodes and nets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .cycles import cycle_split
from .geometry import column_extent, stack_lane
from .keys import natural_key
from .topology_boxchain import box_chains
from .topology_chains import (
    Ends,
    Facts,
    MemberDraft,
    chains,
    fold_parallel,
    links_of,
    member_lanes,
    orient_chain,
)
from .topology_check import cell_findings
from .topology_elements import (
    Elem,
    drawn_symbols,
    elements,
    is_wiring,
    net_ends,
    wired_pins,
)
from .topology_lanes import lanes_of
from .topology_nets import Attached, FanEnv, fans_of
from .topology_split import check_acyclic, cut_nets, split_fans
from .values import (
    Column,
    CrossLink,
    End,
    Fan,
    FlowGraph,
    Lane,
    Options,
    PinRef,
    PlacementProblem,
    Stand,
    Sym,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .topology_elements import NetEnd
    from .topology_fans import LaneDraft


@dataclass(frozen=True, slots=True)
class ColumnEnv:
    """What column ends read: symbols, options, net to fan id, cross-linked nets, box pins."""

    syms: dict[str, Sym]
    options: Options
    fan_of_net: dict[str, str]
    cross_nets: set[str]
    attached: Attached
    net_of: dict[PinRef, str]


def build_flow(problem: PlacementProblem, options: Options) -> FlowGraph:
    """Pins, nodes, nets and rails in; columns of lanes, fans, cross-links and stands out."""
    wired = wired_pins(problem)
    drawn = {s.id: s for s in drawn_symbols(problem, wired)}
    elems = {e.key: e for s in drawn.values() for e in elements(s, wired)}
    ends, folds = fold_parallel(_ends_of(problem, wired, drawn, elems), elems, drawn)
    ends, chain_lanes, notes = box_chains(ends, drawn, enabled=options.box_columns)
    facts, links = Facts(elems, drawn, ends, dict(wired)), links_of(ends)
    paths = tuple(orient_chain(p, facts) for p in chains(links, elems, _dealt(ends, folds)))
    lanes, slot = lanes_of(paths, elems, drawn)
    lanes += [*member_lanes(folds, lanes, facts, options), *chain_lanes]
    bundles = {n.id: n.bundle for n in problem.nets if n.bundle}
    fans, cross, attached = fans_of(ends, links, FanEnv(slot, lanes, elems, drawn, bundles))
    env = ColumnEnv(drawn, options, *_nets_of(fans, cross), attached, facts.net_of)
    columns, fans, cross = _split_cycles(lanes, env, fans, cross)
    return FlowGraph(
        columns,
        fans,
        cross,
        _stands(problem, drawn),
        cycle_split(problem),
        tuple(sorted(drawn, key=natural_key)),
        (*cell_findings(drawn, elems, columns), *notes),
    )


def _dealt(ends: Mapping[str, tuple[NetEnd, ...]], folds: Mapping[str, Sequence[str]]) -> set[str]:
    """Elements that start no chain: through ends of fan nets and the members of a fold."""
    dealt = {e.elem or "" for es in ends.values() for e in es if e.site == "through" and e.elem}
    return dealt | {m for ms in folds.values() for m in ms}


def _split_cycles(
    lanes: Sequence[LaneDraft], env: ColumnEnv, fans: tuple[Fan, ...], cross: tuple[CrossLink, ...]
) -> tuple[tuple[Column, ...], tuple[Fan, ...], tuple[CrossLink, ...]]:
    """Columns of the flow; a net that closes a y cycle leaves its fan and they are built again."""
    columns = _columns(lanes, env)
    cuts = cut_nets(columns, fans, env.net_of)
    if cuts:
        fans, cross = split_fans(fans, cross, cuts, env.net_of)
        fan_of_net, cross_nets = _nets_of(fans, cross)
        columns = _columns(lanes, replace(env, fan_of_net=fan_of_net, cross_nets=cross_nets))
    check_acyclic(columns, fans)
    return columns, fans, cross


def _ends_of(
    problem: PlacementProblem,
    wired: Mapping[PinRef, str],
    drawn: Mapping[str, Sym],
    elems: Mapping[str, Elem],
) -> Ends:
    elem_of_pin = {
        PinRef(e.sym, p.id): e
        for e in elems.values()
        for p in drawn[e.sym].pins
        if e.form == "free" or p.id in (e.n_pin, e.s_pin)
    }
    live = set(wired.values())
    return {
        n.id: net_ends(n, elem_of_pin, drawn) for n in problem.nets if is_wiring(n) and n.id in live
    }


def _nets_of(
    fans: tuple[Fan, ...], cross: tuple[CrossLink, ...]
) -> tuple[dict[str, str], set[str]]:
    return {net: f.id for f in fans for net in f.nets}, {c.net for c in cross}


def _rail_rank(problem: PlacementProblem, ref: PinRef) -> int:
    return next((n.rail.rank for n in problem.nets if n.rail and ref in n.pins), 0)


def _stands(problem: PlacementProblem, drawn: Mapping[str, Sym]) -> tuple[Stand, ...]:
    return tuple(
        Stand(s.id, p.id, p.stand, _rail_rank(problem, PinRef(s.id, p.id)))
        for s in sorted(drawn.values(), key=lambda s: natural_key(s.id))
        for p in s.pins
        if p.stand
    )


def _columns(lanes: Sequence[LaneDraft], env: ColumnEnv) -> tuple[Column, ...]:
    syms = env.syms
    by_col: dict[str, list[LaneDraft]] = defaultdict(list)
    for lane in lanes:
        by_col[lane.column].append(lane)
    out = []
    for col, drafts in by_col.items():
        drafts.sort(key=lambda d: d.index)
        heads = tuple(_end(d, 0, env, env.attached.get((col, d.index, "head"))) for d in drafts)
        feet = tuple(_end(d, -1, env, env.attached.get((col, d.index, "foot"))) for d in drafts)
        lanes_v = tuple(Lane(tuple(d.cells), d.offset) for d in drafts)
        column = build_column(col, lanes_v, (heads, feet), syms, env.options)
        out.append(replace(column, hops=drafts[0].hops))
    return tuple(sorted(out, key=lambda c: natural_key(c.id)))


def build_column(
    col_id: str,
    lanes: tuple[Lane, ...],
    ends: tuple[tuple[End, ...], tuple[End, ...]],
    syms: Mapping[str, Sym],
    options: Options,
) -> Column:
    """The one home of a column's height and width: stages 1 and 4 build every column here."""
    in_row = frozenset(s.id for s in syms.values() if s.row_group)
    height = max(stack_lane(syms, ln.cells, options, in_row)[1] for ln in lanes)
    left, right = column_extent(syms, lanes, in_row)
    return Column(col_id, lanes, ends[0], ends[1], height, right - left)


def _end(d: LaneDraft, which: int, env: ColumnEnv, box_pin: PinRef | None) -> End:
    if isinstance(d, MemberDraft):
        return d.ends[which]
    cell = d.cells[which]
    pin_id = cell.top_pin if which == 0 else cell.bottom_pin
    if pin_id is None:
        return End("open")
    pin = next(p for p in env.syms[cell.sym].pins if p.id == pin_id)
    ref = PinRef(cell.sym, pin_id)
    net = env.net_of.get(ref)
    if pin.stand:
        return End("stand", None, ref, pin.stand)
    if box_pin is not None:
        return End("boxpin", net, box_pin)
    if net in env.fan_of_net:
        return End("fan", net, ref, env.fan_of_net[net])
    return End("crosslink", net, ref) if net in env.cross_nets else End("open", net, ref)
