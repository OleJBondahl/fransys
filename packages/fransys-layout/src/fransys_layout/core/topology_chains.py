"""Stage 1, part 2: two-end nets link elements into chains; shared symbols make a column."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
lazy from collections.abc import Set as AbstractSet

from .geometry import lane_extent
from .keys import natural_key
from .topology_elements import Elem, NetEnd
from .topology_fans import LaneDraft
from .unionfind import UnionFind
from .values import Cell, End, Options, Pin, PinRef
lazy from .sym_values import Sym

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .values import Orientation

BOXPIN_WEIGHT = 6
PAIR = 2
Rank = tuple[bool, bool, tuple[tuple[int, int | str], ...]]

Ends = dict[str, tuple[NetEnd, ...]]


@dataclass(frozen=True, slots=True)
class Link:
    """A two-end net between elements a and b, with its through elements in between."""

    net: str
    a: NetEnd
    b: NetEnd
    throughs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Node:
    """An element on a chain path: top is its pin toward the head, bottom toward the foot."""

    elem: str
    top: str | None
    bottom: str | None


@dataclass(frozen=True, slots=True)
class Facts:
    """What head scoring and member lanes read: elements, symbols, net ends, and pin to net."""

    elems: dict[str, Elem]
    syms: dict[str, Sym]
    ends_by_net: Ends
    net_of: dict[PinRef, str]
    end_bias_weight: int
    flip_turn: Orientation
    bundle_of: Mapping[str, str] = field(default_factory=dict)


def links_of(ends_by_net: Ends) -> dict[str, Link]:
    """Nets with exactly two element ends of role top or bottom are chain links.

    Two ends of one role are side by side, not in series: with a through element between
    them (a hub) the net is a fan; with none, the link flips one of them (the turned marker).
    """
    out: dict[str, Link] = {}
    for net, ends in ends_by_net.items():
        outer = [e for e in ends if e.site in ("top", "bottom")]
        others = [e for e in ends if e.site not in ("top", "bottom", "through")]
        throughs = tuple(e.elem for e in ends if e.site == "through" and e.elem)
        series = len(outer) == PAIR and outer[0].site != outer[1].site
        if len(outer) == PAIR and not others and (series or not throughs):
            out[net] = Link(net, outer[0], outer[1], throughs)
    return out


def _break_cycles(links: Mapping[str, Link]) -> dict[str, Link]:
    """Each element has two slots, so links form paths and cycles; a cycle loses its last net."""
    uf = UnionFind()
    kept: dict[str, Link] = {}
    for net in sorted(links, key=natural_key):
        link = links[net]
        if uf.same(link.a.elem or "", link.b.elem or ""):
            continue
        uf.union(link.a.elem or "", link.b.elem or "")
        kept[net] = link
    return kept


def chains(
    links: Mapping[str, Link], elems: Mapping[str, Elem], dealt: AbstractSet[str]
) -> tuple[tuple[Node, ...], ...]:
    """Every element on a path, as nodes from one extreme to the other; lone elements are one node.

    Elements in dealt (through ends of fan nets) start no chain: the fan stage places them.
    """
    kept = _break_cycles(links)
    adj: dict[str, list[Link]] = defaultdict(list)
    for link in kept.values():
        adj[link.a.elem].append(link)  # ty: ignore[invalid-argument-type] - link ends are elements
        adj[link.b.elem].append(link)  # ty: ignore[invalid-argument-type] - as above
    skip = {t for link in kept.values() for t in link.throughs} | dealt
    starts = [k for k in sorted(elems, key=natural_key) if len(adj[k]) <= 1 and k not in skip]
    seen: set[str] = set()
    paths: list[tuple[Node, ...]] = []
    for start in starts:
        if start not in seen:
            paths.append(_walk(start, adj, elems))
            seen.update(n.elem for n in paths[-1])
    return tuple(paths)


def _walk(
    start: str, adj: Mapping[str, Sequence[Link]], elems: Mapping[str, Elem]
) -> tuple[Node, ...]:
    nodes: list[Node] = []
    prev_pin: str | None = None
    cur = start
    came: Link | None = None
    while True:
        nxt = next((link for link in adj[cur] if link is not came), None)
        if nxt is None:
            nodes.append(_complete(cur, prev_pin, None, elems))
            return tuple(nodes)
        near, far = (nxt.a, nxt.b) if nxt.a.elem == cur else (nxt.b, nxt.a)
        nodes.append(_complete(cur, prev_pin, near.pin.pin, elems))
        nodes.extend(Node(t, elems[t].n_pin, elems[t].s_pin) for t in nxt.throughs)
        prev_pin, cur, came = far.pin.pin, far.elem or "", nxt


def _complete(key: str, top: str | None, bottom: str | None, elems: Mapping[str, Elem]) -> Node:
    """A path end shows its unused pin to the world; a lone element shows n up and s down."""
    e = elems[key]
    if top is None and bottom is None:
        return Node(key, e.n_pin, e.s_pin)
    if top is None:
        return Node(key, e.s_pin if bottom == e.n_pin else e.n_pin, bottom)
    if bottom is None:
        return Node(key, top, e.s_pin if top == e.n_pin else e.n_pin)
    return Node(key, top, bottom)


def _end_score(node: Node, pin_id: str | None, facts: Facts) -> int:
    """How much this extreme wants to be head: box pins first, biased ends, then the side."""
    if pin_id is None:
        return 0
    sym = facts.syms[facts.elems[node.elem].sym]
    pin = _pin_of(sym, pin_id)
    side = {"N": 1, "S": -1}.get(pin.side, 0)
    if pin.end_bias:
        return side - pin.end_bias * facts.end_bias_weight
    return side + _boxpin_bias(PinRef(sym.id, pin_id), facts)


def _pin_of(sym: Sym, pin_id: str) -> Pin:
    return next(p for p in sym.pins if p.id == pin_id)


def _boxpin_bias(ref: PinRef, facts: Facts) -> int:
    """Plus the weight when the net meets a box pin on its S side (head below it), else minus."""
    net = facts.net_of.get(ref)
    box_ends = [e for e in facts.ends_by_net.get(net or "", ()) if e.site == "boxpin"]
    if not box_ends:
        return 0
    box = box_ends[0].pin
    return BOXPIN_WEIGHT if _pin_of(facts.syms[box.sym], box.pin).side == "S" else -BOXPIN_WEIGHT


def orient_chain(
    path: tuple[Node, ...], facts: Facts, *, turn: bool | None = None
) -> tuple[Node, ...]:
    """Put the head first: the extreme that scores higher, the first on a tie; turn forces it."""
    if turn is None:
        turn = _end_score(path[-1], path[-1].bottom, facts) > _end_score(
            path[0], path[0].top, facts
        )
    if turn:
        return tuple(Node(n.elem, n.bottom, n.top) for n in reversed(path))
    return path


def orient_chains(
    paths: Sequence[tuple[Node, ...]], facts: Facts, *, together: bool
) -> tuple[tuple[Node, ...], ...]:
    """Orient every chain; the chains of one bundle turn together, by their summed scores (BUNDLE).

    Every pin pair of a device takes the bundle's direction, never one direction per chain.
    """
    groups: dict[frozenset[str], list[int]] = defaultdict(list)
    for i, path in enumerate(paths):
        if together and (bundles := _bundles_of(path, facts)):
            groups[bundles].append(i)
    flip = {i for ids in groups.values() if _group_flips(ids, paths, facts) for i in ids}
    bundled = {i for ids in groups.values() for i in ids}
    return tuple(
        orient_chain(p, facts, turn=i in flip if i in bundled else None)
        for i, p in enumerate(paths)
    )


def _bundles_of(path: tuple[Node, ...], facts: Facts) -> frozenset[str]:
    """The bundle ids of the nets a chain's end pins meet."""
    pins = ((n.elem, pin) for n in path for pin in (n.top, n.bottom) if pin)
    nets = (facts.net_of.get(PinRef(facts.elems[e].sym, pin)) for e, pin in pins)
    return frozenset(facts.bundle_of[n] for n in nets if n is not None and n in facts.bundle_of)


def _group_flips(ids: Sequence[int], paths: Sequence[tuple[Node, ...]], facts: Facts) -> bool:
    gain = 0
    for i in ids:
        path = paths[i]
        gain += _end_score(path[-1], path[-1].bottom, facts) - _end_score(
            path[0], path[0].top, facts
        )
    return gain > 0


def cells_of(
    path: tuple[Node, ...],
    elems: Mapping[str, Elem],
    syms: Mapping[str, Sym],
    flip_turn: Orientation,
) -> tuple[Cell, ...]:
    """Head to foot; the flip turn when an s pin points at the head or an n pin at the foot."""
    out: list[Cell] = []
    for node in path:
        e = elems[node.elem]
        orient = flip_turn if _flipped(node, e) and flip_turn in syms[e.sym].views else "R0"
        out.append(Cell(e.sym, orient, node.top, node.bottom))
    return tuple(out)


def _flipped(node: Node, e: Elem) -> bool:
    if e.form == "free":
        return False
    return (node.top is not None and node.top == e.s_pin) or (
        node.bottom is not None and node.bottom == e.n_pin
    )


def group_columns(
    paths: tuple[tuple[Node, ...], ...], elems: Mapping[str, Elem]
) -> tuple[tuple[int, ...], ...]:
    """Chains that share a symbol are lanes of one column; each group lists its chain indexes."""
    uf = UnionFind()
    first_chain: dict[str, int] = {}
    for i, path in enumerate(paths):
        for node in path:
            j = first_chain.setdefault(elems[node.elem].sym, i)
            uf.union(str(j), str(i))
    groups: dict[str, list[int]] = defaultdict(list)
    for i in range(len(paths)):
        groups[uf.find(str(i))[0]].append(i)
    return tuple(tuple(sorted(v)) for _, v in sorted(groups.items(), key=lambda kv: min(kv[1])))


@dataclass(slots=True)
class MemberDraft(LaneDraft):
    """A folded parallel member alone in a lane of the parent's column; ends are its joins."""

    ends: tuple[End, ...] = ()


def fold_parallel(
    ends_by_net: Ends, elems: Mapping[str, Elem], syms: Mapping[str, Sym]
) -> tuple[Ends, dict[str, tuple[str, ...]]]:
    """Two or more pin pairs on the same two nets, either way up, fold into one column, a lane each.

    The parent keeps the nets and its chain; the members leave them, and a net left with fewer
    than two ends is dropped. Returns the thinned ends and parent key to member keys.
    """
    folds = _parallel_groups(ends_by_net, elems, syms)
    members = {m for ms in folds.values() for m in ms}
    out: Ends = {}
    for net, ends in ends_by_net.items():
        kept = tuple(e for e in ends if e.elem not in members)
        if len(kept) == len(ends) or len(kept) >= PAIR:
            out[net] = kept
    return out, folds


def _nets_by_role(ends_by_net: Ends) -> dict[str, dict[str, str]]:
    """Element key to {role: net} over its top and bottom ends."""
    on: dict[str, dict[str, str]] = defaultdict(dict)
    for net, ends in ends_by_net.items():
        for e in ends:
            if e.site in ("top", "bottom") and e.elem:
                on[e.elem][e.site] = net
    return on


def _parallel_groups(
    ends_by_net: Ends, elems: Mapping[str, Elem], syms: Mapping[str, Sym]
) -> dict[str, tuple[str, ...]]:
    """Group the pin pairs of one-element symbols by their unordered pair of nets.

    Out of scope: a longer series run, pin pairs of one multi-pair symbol, and a group whose net
    carries a hub (a through end): the fan draws that.
    """
    on = _nets_by_role(ends_by_net)
    per_sym = Counter(e.sym for e in elems.values())
    by_pair: dict[frozenset[str], list[str]] = defaultdict(list)
    for key in sorted(on, key=natural_key):
        if elems[key].form == "pole" and per_sym[elems[key].sym] == 1 and len(on[key]) == PAIR:
            by_pair[frozenset(on[key].values())].append(key)
    out: dict[str, tuple[str, ...]] = {}
    for pair, keys in by_pair.items():
        if len(keys) >= PAIR and not any(e.site == "through" for n in pair for e in ends_by_net[n]):
            parent = _pick_parent(keys, pair, ends_by_net, elems, syms)
            out[parent] = tuple(k for k in keys if k != parent)
    return out


def _parent_rank(key: str, sym: Sym, outside: AbstractSet[str | None]) -> Rank:
    return sym.child_of is not None, sym.item is None or sym.item not in outside, natural_key(key)


def _pick_parent(
    keys: Sequence[str],
    pair: frozenset[str],
    ends_by_net: Ends,
    elems: Mapping[str, Elem],
    syms: Mapping[str, Sym],
) -> str:
    """The member that is no child item, then the one sharing its item with an outside element."""
    outside = {
        syms[elems[e.elem].sym].item
        for net in pair
        for e in ends_by_net[net]
        if e.elem and e.elem not in keys
    }

    syms_of = {k: syms[elems[k].sym] for k in keys}
    return min(keys, key=lambda k: _parent_rank(k, syms_of[k], outside))


def _pin_refs(cell: Cell) -> tuple[PinRef, PinRef]:
    return PinRef(cell.sym, cell.top_pin or ""), PinRef(cell.sym, cell.bottom_pin or "")


def member_offset(
    column: Sequence[LaneDraft], cells: tuple[Cell, ...], syms: Mapping[str, Sym], gap: Options
) -> int:
    """The member's x: right of the column's widest lane edge, plus the gap, on the wiring grid."""
    in_row = frozenset(s.id for s in syms.values() if s.row_group)
    left, _ = lane_extent(syms, cells, in_row)
    edge = max(lane.offset + lane_extent(syms, tuple(lane.cells), in_row)[1] for lane in column)
    return -(-(edge + gap.column_gap_min - left) // gap.wiring_grid) * gap.wiring_grid


def member_lanes(
    folds: Mapping[str, tuple[str, ...]], lanes: Sequence[LaneDraft], facts: Facts, options: Options
) -> list[MemberDraft]:
    """One lane per member, right of the parent's column, its pins on the parent's two nets.

    The head and foot ends are joins to the lane on the left (the parent's pin for the first
    member, the previous member's for the next), which stage 6 draws.
    """
    out: list[MemberDraft] = []
    for parent in sorted(folds, key=natural_key):
        sym = facts.elems[parent].sym
        home = next(lane for lane in lanes if any(c.sym == sym for c in lane.cells))
        top, bottom = _pin_refs(next(c for c in home.cells if c.sym == sym))
        nets = (facts.net_of[top], facts.net_of[bottom])
        for key in folds[parent]:
            column = [lane for lane in (*lanes, *out) if lane.column == home.column]
            cell = _member_cell(facts.elems[key], nets, facts)
            offset = member_offset(column, (cell,), facts.syms, options)
            ends = (End("join", nets[0], top), End("join", nets[1], bottom))
            out.append(
                MemberDraft(
                    home.column, 1 + max(lane.index for lane in column), [cell], offset, ends
                )
            )
            top, bottom = _pin_refs(cell)
    return out


def _member_cell(e: Elem, nets: tuple[str, str], facts: Facts) -> Cell:
    """The member's cell: its pin on the parent's top net up, its pin on the bottom net down."""
    pins = {facts.net_of[PinRef(e.sym, p)]: p for p in (e.n_pin, e.s_pin) if p}
    node = Node(e.key, pins[nets[0]], pins[nets[1]])
    return cells_of((node,), facts.elems, facts.syms, facts.flip_turn)[0]
