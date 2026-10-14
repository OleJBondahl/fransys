"""The unit level folded to function groups (O3), and the dispatch to an opened group (O3a).

Each function group is one box with its counts, one line joins each pair of boxes per kind, and
the connections leaving the unit are stubs folded by far end (O3b). A unit with fewer than two
groups opens straight to its devices. Reached as `derive.fold_level` (model-0199).
"""

from typing import Any, cast

from fransys_model.kernel import SchemaError
from fransys_model.layout import OverviewRef, OverviewRefKind
from fransys_model.vocab.membership import require
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Unit

from .memo import Memo
from .overview_conns import Conn, unit_connections
from .overview_group_view import Lifted, Scope, merged_lines, open_group, strip_notes
from .overview_groups import (
    box_groups,
    box_order_key,
    fold_box,
    fold_key,
    group_box,
    strips_box,
)
from .overview_levels import level_box, overview_level
from .overview_stubs import RawStub, fold_stubs, outside_stub
from .rows import ItemKind, OverviewBox
from .rows_overview import FoldBox, FoldLevel

__all__ = ["fold_level"]

_FOLD_MIN = 2


def _keymap(
    boxes: tuple[OverviewBox, ...], groups: dict[Id[Any], Id[AspectNode] | None]
) -> dict[Id[Any], OverviewRef]:
    """The folded key of each box: its group, else the strips box, else its own."""
    found = {}
    for box in boxes:
        group = groups[box.box]
        if group is not None:
            found[box.box] = OverviewRef(kind=OverviewRefKind.GROUP, node=group)
        elif box.kind is ItemKind.STRIP:
            found[box.box] = OverviewRef(kind=OverviewRefKind.STRIPS)
        else:
            found[box.box] = fold_key(box)
    return found


def _folded_boxes(
    model: Model, members: dict[OverviewRef, list[OverviewBox]], inner: dict[OverviewRef, int]
) -> tuple[FoldBox, ...]:
    """One fold box per key, in text order."""
    made = [
        group_box(model, cast("Id[AspectNode]", key.node), held, inner.get(key, 0))
        if key.kind is OverviewRefKind.GROUP
        else strips_box(held)
        if key.kind is OverviewRefKind.STRIPS
        else fold_box(held[0])
        for key, held in members.items()
    ]
    return tuple(sorted(made, key=box_order_key))


def _lift(
    model: Model, unit: Id[Unit], conns: tuple[Conn, ...], keymap: dict[Id[Any], OverviewRef]
) -> tuple[
    dict[tuple[OverviewRef, OverviewRef], list[Conn]], dict[OverviewRef, int], list[RawStub]
]:
    """The connections between boxes by key pair, those inside a group, and the stubs leaving."""
    pairs: dict[tuple[OverviewRef, OverviewRef], list[Conn]] = {}
    inner: dict[OverviewRef, int] = {}
    raws: list[RawStub] = []
    for conn in conns:
        one, two = level_box(model, conn.a, unit), level_box(model, conn.b, unit)
        if one is None or two is None:
            inside = one if two is None else two
            if inside is not None:
                raws.append(outside_stub(model, unit, keymap[inside], conn, inside_a=two is None))
        elif one != two and keymap[one] == keymap[two]:
            inner[keymap[one]] = inner.get(keymap[one], 0) + 1
        elif one != two:
            pairs.setdefault((keymap[one], keymap[two]), []).append(conn)
    return pairs, inner, raws


def _folded(
    model: Model,
    unit: Id[Unit],
    boxes: tuple[OverviewBox, ...],
    groups: dict[Id[Any], Id[AspectNode] | None],
) -> FoldLevel:
    """`unit` folded: group boxes, standing boxes, one line per pair and kind, folded stubs."""
    keymap = _keymap(boxes, groups)
    members: dict[OverviewRef, list[OverviewBox]] = {}
    for box in boxes:
        members.setdefault(keymap[box.box], []).append(box)
    pairs, inner, raws = _lift(model, unit, unit_connections(model, unit), keymap)
    folded = _folded_boxes(model, members, inner)
    rank = {box.key: at for at, box in enumerate(folded)}
    lifted = [Lifted(a, b, c, None) for (a, b), cs in pairs.items() for c in cs]
    lines = merged_lines(model, unit, lifted, rank)
    return FoldLevel(
        unit=unit,
        opened=None,
        folded=True,
        boxes=folded,
        lines=lines,
        stubs=fold_stubs(model, unit, raws, rank),
        strips=strip_notes(boxes, {b.box for b in boxes if b.kind is ItemKind.STRIP}, {}),
    )


@Memo
def _groups(model: Model, unit: Id[Unit]) -> dict[Id[Any], Id[AspectNode] | None]:
    """The group of each box of `unit`'s level, built once per unit."""
    return box_groups(model, unit, overview_level(model, unit).boxes)


def _checked(model: Model, unit: Id[Unit], scope: Scope, groups: dict[Id[Any], Any]) -> None:
    """Refuse a group the unit does not hold, a strips box it does not draw, or a strip it lacks."""
    boxes = overview_level(model, unit).boxes
    if scope.strip is not None:
        strips = {b.box for b in boxes if b.kind is ItemKind.STRIP}
        require(scope.strip if scope.strip in strips else None, "terminal strip", unit)
    opened = scope.opened
    if opened is None:
        return
    if opened.kind is OverviewRefKind.GROUP:
        require(opened.node if opened.node in groups.values() else None, "function group", unit)
        return
    bare = any(b.kind is ItemKind.STRIP and groups[b.box] is None for b in boxes)
    require(opened if opened.kind is OverviewRefKind.STRIPS and bare else None, "strips box", unit)


@Memo
def _fold_level(model: Model, unit: Id[Unit], scope: Scope, *, fold: bool) -> FoldLevel:
    """`fold_level`, built once per unit, scope and fold."""
    level = overview_level(model, unit)
    groups = _groups(model, unit)
    named = {g for g in groups.values() if g is not None}
    _checked(model, unit, scope, groups)
    if scope.opened is None and fold and len(named) >= _FOLD_MIN:
        if scope.strip is not None:
            msg = "the groups view opens no strip"
            raise SchemaError(msg, kind="overview_level")
        return _folded(model, unit, level.boxes, groups)
    return open_group(model, unit, level.boxes, groups, scope)


def fold_level(
    model: Model,
    unit: Id[Unit],
    opened: OverviewRef | None = None,
    *,
    fold: bool = True,
    strip: Id[Item] | None = None,
) -> FoldLevel:
    """`unit`'s level folded to its function groups, or one group or the strips box opened.

    With no `opened`: one box per group (its item, nested-unit and strip counts, and the
    connections inside it), the strips with no group as "Terminal strips (n)", every other item and
    nested unit as itself; one line per pair of boxes and kind with the connections lifted into it;
    stubs folded by far end. A unit with fewer than two groups opens straight: its devices, as an
    opened group is drawn, `folded` false. With a `GROUP`, its devices with a terminal that passes
    wires through drawn as a line labelled with its strip, the rest as `strips` or boxes. With
    `STRIPS`, the strips with no group as boxes, their wires to other boxes ending at stubs.
    With `fold` false and no `opened`, a unit of several groups opens straight too: all its
    devices, strips see-through (the all-devices view, O16). A `strip` of the level opened in it
    stands as its terminals; the groups view opens none.
    Raises `SchemaError` for a group or strips box the unit does not hold, or a `strip` it lacks.
    """
    return _fold_level(model, unit, Scope(opened, strip), fold=fold)
