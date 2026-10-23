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
    orient_chains,
)
from .topology_check import cell_findings
from .topology_elements import (
    Elem,
    elements,
    net_ends,
    wired_pins,
)
from .topology_lanes import lanes_of
from .topology_nets import Attached, FanEnv, cross_link, fans_split
from .topology_split import (
    bundle_conflicts,
    check_acyclic,
    cut_nets,
    split_conflict_ends,
    split_fans,
)
from .topology_tree import TreeFold, source_first, tree_folds, tree_member_lanes
from .values import (
    BiasedEnd,
    Column,
    CrossLink,
    End,
    Fan,
    FlowGraph,
    Lane,
    Options,
    PinRef,
    PlacementProblem,
)
lazy from .sym_values import Sym

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .topology_chains import Link
    from .topology_elements import NetEnd
    from .topology_fans import LaneDraft, Slot
    from .values import Bundle


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
    """Pins, nodes and nets in; columns of lanes, fans, cross-links and biased ends out."""
    wired = wired_pins(problem)
    drawn = {s.id: s for s in problem.symbols}
    elems = {e.key: e for s in drawn.values() for e in elements(s, wired)}
    ends, folds, tree = _folded(problem, _ends_of(problem, wired, drawn, elems), elems, drawn)
    ends, chain_lanes, notes = box_chains(ends, drawn, options, problem.facts.series)
    facts = Facts(
        elems,
        drawn,
        ends,
        dict(wired),
        options.end_bias_weight,
        options.flip_turn,
        {net: b.id for net, b in _bundles(problem).items()},
    )
    links = links_of(ends)
    lanes, slot = _laid(links, (ends, folds, tree), facts, (options, chain_lanes))
    fans, cross, attached = fans_split(
        ends, links, FanEnv(slot, lanes, elems, drawn, _bundles(problem), options.bundle_direction)
    )
    env = ColumnEnv(drawn, options, *_nets_of(fans, cross), attached, facts.net_of)
    env, cross = _unseat_boxes(lanes, env, fans, cross, ends)
    columns, fans, cross = _split_cycles(lanes, env, fans, cross)
    order = tuple(sorted(drawn, key=natural_key))
    return FlowGraph(
        columns,
        fans,
        cross,
        _biased(drawn, order),
        cycle_split(problem),
        order,
        (*cell_findings(drawn, elems, columns), *notes),
    )


def _laid(
    links: Mapping[str, Link],
    parts: tuple[Ends, Mapping[str, tuple[str, ...]], tuple[TreeFold, ...]],
    facts: Facts,
    more: tuple[Options, Sequence[LaneDraft]],
) -> tuple[list[LaneDraft], Slot]:
    """The chains oriented source first as lanes, then the members of folds and trees, boxes."""
    (ends, folds, tree), (options, chain_lanes) = parts, more
    paths = chains(links, facts.elems, _dealt(ends, folds, tree))
    oriented = orient_chains(paths, facts, together=options.bundle_direction)
    lanes, slot = lanes_of(
        source_first(oriented, tree, facts), facts.elems, facts.syms, options.flip_turn
    )
    return [*lanes, *_members((folds, tree), lanes, facts, options), *chain_lanes], slot


def _bundles(problem: PlacementProblem) -> dict[str, Bundle]:
    return {n.id: n.bundle for n in problem.nets if n.bundle}


def _folded(
    problem: PlacementProblem, ends: Ends, elems: Mapping[str, Elem], drawn: Mapping[str, Sym]
) -> tuple[Ends, dict[str, tuple[str, ...]], tuple[TreeFold, ...]]:
    """The ends without the series-parallel trees' joined poles, then without the folds' members."""
    ends, tree = tree_folds(problem.facts.series, ends, elems, drawn)
    ends, folds = fold_parallel(ends, elems, drawn)
    return ends, folds, tree


def _members(
    folds: tuple[Mapping[str, tuple[str, ...]], Sequence[TreeFold]],
    lanes: Sequence[LaneDraft],
    facts: Facts,
    options: Options,
) -> list[MemberDraft]:
    """The folds' member lanes, then the trees' joined lanes, which may join a member lane."""
    out = member_lanes(folds[0], lanes, facts, options)
    return [*out, *tree_member_lanes(folds[1], [*lanes, *out], facts, options)]


def _dealt(
    ends: Mapping[str, tuple[NetEnd, ...]],
    folds: Mapping[str, Sequence[str]],
    tree: Sequence[TreeFold],
) -> set[str]:
    """Elements that start no chain: through ends of fan nets and the members of a fold."""
    dealt = {
        e.elem or ""
        for es in ends.values()
        if len(es) > 1
        for e in es
        if e.site == "through" and e.elem
    }
    return dealt | {m for ms in folds.values() for m in ms} | {m for f in tree for m in f.members}


def _unseat_boxes(
    lanes: Sequence[LaneDraft],
    env: ColumnEnv,
    fans: tuple[Fan, ...],
    cross: tuple[CrossLink, ...],
    ends: Ends,
) -> tuple[ColumnEnv, tuple[CrossLink, ...]]:
    """A bundle's driver column that stands on a box a leg also stands on leaves the box (BUNDLE).

    Its box-pin net is drawn as a cross-link wire, so the driver is not pinned to the box's node.
    """
    stand = {
        a.column for _, _, drivers in bundle_conflicts(_columns(lanes, env), fans) for a in drivers
    }
    drop = {k: pin for k, pin in env.attached.items() if k[0] in stand}
    if not drop:
        return env, cross
    nets = tuple(
        dict.fromkeys(env.net_of[pin] for pin in drop.values())
    )  # fans_of walks nets sorted
    links = tuple(cross_link(n, [e for e in ends[n] if e.site != "through"], lanes) for n in nets)
    attached = {k: v for k, v in env.attached.items() if k not in drop}
    return replace(env, attached=attached, cross_nets=env.cross_nets | set(nets)), cross + links


def _split_cycles(
    lanes: Sequence[LaneDraft], env: ColumnEnv, fans: tuple[Fan, ...], cross: tuple[CrossLink, ...]
) -> tuple[tuple[Column, ...], tuple[Fan, ...], tuple[CrossLink, ...]]:
    """Columns of the flow; a net that closes a y cycle leaves its fan and they are built again.

    First a fan's legs on its drivers' node leave it alone, as cross links (R418).
    """
    fans, cross = split_conflict_ends(_columns(lanes, env), fans, cross)
    env = replace(env, cross_nets=_nets_of(fans, cross)[1])
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
    return {n.id: net_ends(n, elem_of_pin, drawn) for n in problem.nets if n.id in live}


def _nets_of(
    fans: tuple[Fan, ...], cross: tuple[CrossLink, ...]
) -> tuple[dict[str, str], set[str]]:
    return {net: f.id for f in fans for net in f.nets}, {c.net for c in cross}


def _biased(drawn: Mapping[str, Sym], order: Sequence[str]) -> tuple[BiasedEnd, ...]:
    return tuple(
        BiasedEnd(s.id, p.id, p.end_rank)
        for s in (drawn[i] for i in order)
        for p in s.pins
        if p.end_bias
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
    if pin.end_bias:
        return End("biased", None, ref)
    if box_pin is not None:
        return End("boxpin", net, box_pin)
    if net in env.fan_of_net:
        return End("fan", net, ref, fan=env.fan_of_net[net])
    return End("crosslink", net, ref) if net in env.cross_nets else End("open", net, ref)
