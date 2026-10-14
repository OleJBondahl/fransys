"""The findings layer's data: per view, the worst severity and its count on each box and line (O18).

A box's number counts the distinct findings of its worst severity (a finding with several subjects
on one box counts once); the box also carries every finding it holds, each once, for the panel.

A finding's subjects resolve to items and units. A subject not drawn on a view counts on its
nearest drawn ancestor box (the item's parents, its strip box, its group, its field box, then its
units outward); a subject with no drawn ancestor is left out of that view.
"""

from typing import TYPE_CHECKING, Any

from fransys_model.derive import (
    ItemKind,
    effective_placement,
    field_devices,
    item_kind,
    item_of_port,
)
from fransys_model.derive.order import finding_order_key
from fransys_model.kernel import Severity, parent_chain
from fransys_model.vocab import Aspect, conductors, functions, items, units

from ._data_places import holds_of

if TYPE_CHECKING:
    from fransys_model.derive import ViewRows
    from fransys_model.kernel import Finding, Id, Model

    from ._data import _Tables

Key = tuple[str, int | None]
Tally = dict[int, dict[int, int]]  # at -> {finding index: its severity rank}
_RANK = {Severity.INFO: 0, Severity.WARNING: 1, Severity.ERROR: 2}
_ENDS = 2
_NAME = {0: "info", 1: "warning", 2: "error"}


def _unit_keys(tables: _Tables, unit: Id[Any] | None) -> list[Key]:
    """The unit boxes from `unit` outward."""
    found: list[Key] = []
    while unit is not None:
        found.append(("unit", tables.unit_ix.get(unit)))
        unit = units(tables.model)[unit].parent
    return found


def _item_keys(tables: _Tables, item: Id[Any], view_unit: Id[Any] | None) -> list[Key]:
    """The boxes that can hold `item`, nearest first; `view_unit` is the unit of the level."""
    model = tables.model
    chain = list(parent_chain(lambda one: items(model)[one].parent, item))
    keys: list[Key] = [("item", tables.item_ix.get(one)) for one in chain]
    owner = items(model)[item].unit
    if owner is not None and owner == view_unit:
        if any(item_kind(model, one) is ItemKind.STRIP for one in chain):
            keys.append(("strips", None))
        node = effective_placement(model, item, Aspect.FUNCTION)
        keys.append(("group", tables.aspect_ix.get(node)))
    field = field_devices(model).get(item)
    keys.append(("fields", None if field is None else tables.unit_ix.get(field)))
    return [*keys, *_unit_keys(tables, owner)]


def _lookup(tables: _Tables, rows: ViewRows) -> dict[Key, int]:
    """Each drawn box by the key of its reference; a place box also by each member it holds."""
    found: dict[Key, int] = {}
    for index, box in enumerate(rows.boxes):
        if box.key.at is not None:
            continue
        kind, ix = tables.ref(box.key.ref) or ("", None)
        found.setdefault((kind, ix), index)
        for (held_kind, held_ix), _label in holds_of(tables, box) or ():
            found.setdefault((held_kind, held_ix), index)
    return found


def _box_of(keys: list[Key], lookup: dict[Key, int]) -> int | None:
    """The first drawn box among `keys`; a key with no table index names nothing."""
    named = [k for k in keys if k[1] is not None or k[0] == "strips"]
    return next((lookup[k] for k in named if k in lookup), None)


def _ends(model: Model, subject: Id[Any]) -> list[Id[Any]]:
    """The items a subject names: itself, its port's or function's item, a conductor's two ends."""
    if subject.kind == "item":
        return [subject]
    if subject.kind == "port":
        return [item_of_port(model, subject)]
    if subject.kind == "function":
        return [functions(model)[subject].item]
    if subject.kind == "conductor":
        record = conductors(model)[subject]
        return [item_of_port(model, record.a), item_of_port(model, record.b)]
    return []


def _hit(tally: Tally, at: int, which: int, rank: int) -> None:
    tally.setdefault(at, {})[which] = rank


def _boxes_of(
    tables: _Tables, rows: ViewRows, lookup: dict[Key, int], subject: Id[Any]
) -> list[int]:
    """The drawn boxes a subject counts on, in the order of its ends."""
    if subject.kind == "unit":
        keys = [_unit_keys(tables, subject)]
    else:
        keys = [_item_keys(tables, one, rows.unit) for one in _ends(tables.model, subject)]
    found = [_box_of(k, lookup) for k in keys]
    return [at for at in found if at is not None]


def _wires_of(rows: ViewRows, subject: Id[Any], ends: list[int]) -> list[int]:
    """The lines a subject counts on: a cable item's own lines, a conductor's between its ends."""
    if subject.kind == "item":
        return [i for i, line in enumerate(rows.lines) if line.via == subject]
    pair = {rows.boxes[e].key for e in ends}
    if subject.kind != "conductor" or len(pair) != _ENDS:
        return []
    return [i for i, line in enumerate(rows.lines) if {line.a, line.b} == pair]


def _count(
    tables: _Tables,
    rows: ViewRows,
    lookup: dict[Key, int],
    which: tuple[int, Finding],
    tallies: tuple[Tally, Tally],
) -> None:
    """Add one finding's subjects to the view's box and line tallies."""
    boxes, lines = tallies
    index, finding = which
    rank = _RANK[finding.severity]
    for subject in finding.subjects:
        ends = _boxes_of(tables, rows, lookup, subject)
        if wires := _wires_of(rows, subject, ends):
            for at in wires:
                _hit(lines, at, index, rank)
        else:
            for at in dict.fromkeys(ends):
                _hit(boxes, at, index, rank)


def _flat(model: Model, tally: Tally, findings: tuple[Finding, ...]) -> list[list[Any]]:
    """`[index, worst, count, [[severity, code, count, messages], ...]]`, worst code first.

    Messages follow in finding order (FT4); they print designations, never an Id (A10).
    """
    out: list[list[Any]] = []
    for at, held in sorted(tally.items()):
        worst = max(held.values())
        counts: dict[tuple[int, str], list[Finding]] = {}
        for i, rank in held.items():
            counts.setdefault((rank, findings[i].code), []).append(findings[i])
        ordered = sorted(counts.items(), key=lambda one: (-one[0][0], one[0][1]))
        listed = [
            [_NAME[rank], code, len(found), _messages(model, found)]
            for (rank, code), found in ordered
        ]
        out.append([at, _NAME[worst], sum(1 for r in held.values() if r == worst), listed])
    return out


def _messages(model: Model, found: list[Finding]) -> list[str]:
    """The messages of one code's findings in finding order."""
    ordered = sorted(found, key=lambda f: (finding_order_key(model, f), f.message))
    return [f.message for f in ordered]


def findings_data(
    tables: _Tables, drawn: list[ViewRows], findings: tuple[Finding, ...]
) -> list[Any] | None:
    """`[[boxes, lines]]` per view, each `[index, severity, count, finding indexes]`, or `None`.

    `drawn` holds the rows of the views the page has, in the page's order.
    """
    per_view: list[tuple[Tally, Tally]] = []
    for rows in drawn:
        tallies: tuple[Tally, Tally] = ({}, {})
        lookup = _lookup(tables, rows)
        for which in enumerate(findings):
            _count(tables, rows, lookup, which, tallies)
        per_view.append(tallies)
    if not any(boxes or lines for boxes, lines in per_view):
        return None
    return [
        [_flat(tables.model, boxes, findings), _flat(tables.model, lines, findings)]
        for boxes, lines in per_view
    ]


__all__ = ["findings_data"]
