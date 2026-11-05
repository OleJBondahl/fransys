"""Stage 1, part 2b: which end of a chain is its head (FLOW-DOWN, layout-0396).

An anchored end (a box-drawn function beyond it, `Series.anchor`) decides; else the extreme that
scores higher is the head. The chains of one bundle turn together, but never an anchored one.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .topology_chains import Facts, Node, flipped, group_columns
from .values import Pin, PinRef
lazy from .sym_values import Sym

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def _end_score(node: Node, pin_id: str | None, facts: Facts) -> int:
    """How much this extreme wants to be head: box pins first, biased ends, then the side."""
    if pin_id is None:
        return 0
    sym = facts.syms[facts.elems[node.elem].sym]
    pin = _pin_of(sym, pin_id)
    side = {"N": 1, "S": -1}.get(pin.side, 0)
    bias = _boxpin_bias(PinRef(sym.id, pin_id), facts)
    if abs(bias) == facts.anchor_weight:
        return bias
    if pin.end_bias:
        return side - pin.end_bias * facts.end_bias_weight
    return side + bias


def _pin_of(sym: Sym, pin_id: str) -> Pin:
    return next(p for p in sym.pins if p.id == pin_id)


def _boxpin_bias(ref: PinRef, facts: Facts) -> int:
    """Plus the weight when the net meets a box pin on its S side (head below it), else minus.

    An anchored symbol's pin on a box net weighs the anchor: plus at a head, minus at a tail.
    """
    net = facts.net_of.get(ref)
    box_ends = [e for e in facts.ends_by_net.get(net or "", ()) if e.site == "boxpin"]
    if not box_ends:
        return 0
    if ref.sym in facts.anchor_of:
        return facts.anchor_of[ref.sym] * facts.anchor_weight
    box = box_ends[0].pin
    return facts.boxpin_weight if _pin_of(facts.syms[box.sym], box.pin).side == "S" else -facts.boxpin_weight


def orient_chain(path: tuple[Node, ...], facts: Facts, *, turn: bool | None = None) -> tuple[Node, ...]:
    """Put the head first: the extreme that scores higher, the first on a tie; turn forces it."""
    if turn is None:
        turn = _end_score(path[-1], path[-1].bottom, facts) > _end_score(path[0], path[0].top, facts)
    if turn:
        return tuple(Node(n.elem, n.bottom, n.top) for n in reversed(path))
    return path


def orient_chains(paths: Sequence[tuple[Node, ...]], facts: Facts, *, together: bool) -> tuple[tuple[Node, ...], ...]:
    """Orient every chain; the chains of one bundle turn together, by their summed scores (BUNDLE).

    A device's pin pairs take the bundle's direction, never one per chain; an anchored chain
    turns by its anchor (F5). With `together` the chains of one symbol turn as one (one turn drawn).
    """
    groups: dict[frozenset[str], list[int]] = defaultdict(list)
    for i, path in enumerate(paths):
        if together and not _anchored(path, facts) and not _on_box_end(path, facts) and (bundles := _bundles_of(path, facts)):
            groups[bundles].append(i)
    turns = {i: _group_flips(ids, paths, facts) for ids in groups.values() for i in ids}
    if together:
        turns |= _symbol_turns(paths, facts, turns)
    return tuple(orient_chain(p, facts, turn=turns.get(i)) for i, p in enumerate(paths))


def _symbol_turns(paths: Sequence[tuple[Node, ...]], facts: Facts, bundled: Mapping[int, bool]) -> dict[int, bool]:
    """The turn of each chain a bundle does not own: its symbol's bundle turn, else the column's.

    A symbol turns as one (layout-0404, R540): the chain turn that gives the symbol's node the
    same flip as in its bundled chain. An anchored chain keeps its own (layout-0181).
    """
    flip_of = {
        facts.elems[n.elem].sym: flipped(n, facts.elems[n.elem]) for i, turn in bundled.items() for n in orient_chain(paths[i], facts, turn=turn)
    }
    out: dict[int, bool] = {}
    for column in group_columns(paths, facts.elems):
        rest = tuple(i for i in column if i not in bundled)
        column_turn = _group_flips(column, paths, facts) if rest else False
        for i in rest:
            out[i] = column_turn
            if not _anchored(paths[i], facts):
                out[i] = _same_flip(paths[i], facts, flip_of, default=column_turn)
    return out


def _same_flip(path: tuple[Node, ...], facts: Facts, flip_of: Mapping[str, bool], *, default: bool) -> bool:
    """The turn (the default first) that gives the chain's first bundled symbol its flip."""
    for turn in (default, not default):
        for n in orient_chain(path, facts, turn=turn):
            if (sym := facts.elems[n.elem].sym) in flip_of:
                if flipped(n, facts.elems[n.elem]) == flip_of[sym]:
                    return turn
                break
    return default


def _ends(path: tuple[Node, ...]) -> tuple[tuple[Node, str | None], ...]:
    """The chain's two extremes with their outer pins."""
    return (path[0], path[0].top), (path[-1], path[-1].bottom)


def _anchored(path: tuple[Node, ...], facts: Facts) -> bool:
    """True when a box-drawn function anchors either extreme of the chain."""
    return any(abs(_end_score(node, pin, facts)) == facts.anchor_weight for node, pin in _ends(path))


def _on_box_end(path: tuple[Node, ...], facts: Facts) -> bool:
    """True when a box pin is wired to either extreme of a chain with a direction: it keeps out of its bundle's turn (FLOW-DOWN).

    A one-pin symbol alone has none: it turns with its bundle, so a device's pins keep one direction (BUNDLE).
    """
    if len(path) == 1 and None in (path[0].top, path[0].bottom):
        return False
    return any(pin is not None and _boxpin_bias(PinRef(facts.elems[node.elem].sym, pin), facts) != 0 for node, pin in _ends(path))


def _bundles_of(path: tuple[Node, ...], facts: Facts) -> frozenset[str]:
    """The bundle ids of the nets a chain's end pins meet."""
    pins = ((n.elem, pin) for n in path for pin in (n.top, n.bottom) if pin)
    nets = (facts.net_of.get(PinRef(facts.elems[e].sym, pin)) for e, pin in pins)
    return frozenset(facts.bundle_of[n] for n in nets if n is not None and n in facts.bundle_of)


def _group_flips(ids: Sequence[int], paths: Sequence[tuple[Node, ...]], facts: Facts) -> bool:
    gain = 0
    for i in ids:
        path = paths[i]
        gain += _end_score(path[-1], path[-1].bottom, facts) - _end_score(path[0], path[0].top, facts)
    return gain > 0
