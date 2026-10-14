"""The field-device fold of the system level (O9): a unit's field devices as one box beside it.

A field device is an item in no unit, not by others, whose every connection lands in one unit.
`field_devices` is the one function for that fact; `field_fold` groups it by unit. Reached as
`derive.field_devices` and `derive.field_fold` (model-0199).
"""

from typing import Any, cast

from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .block_diagram import box_dashed, box_of, box_order
from .memo import Memo
from .overview import overview_graph
from .rows_overview import FieldFold, FieldJoin
lazy from .rows import OverviewLinkKind

__all__ = ["field_devices", "field_fold"]


@Memo
def field_devices(model: Model) -> dict[Id[Item], Id[Unit]]:
    """Each field device with the one unit all its connections land in.

    The item is in no unit, stands as a box of its own at the system level, is not by others, and
    has at least one connection; every far end sits in the same top-level unit. Nothing is authored.
    """
    far_boxes: dict[Id[Item], set[Id[Any] | None]] = {}
    for link in overview_graph(model).links:
        for near, far in ((link.a, link.b), (link.b, link.a)):
            far_boxes.setdefault(near, set()).add(box_of(model, far, None))
    found: dict[Id[Item], Id[Unit]] = {}
    for item, boxes in far_boxes.items():
        (only,) = boxes if len(boxes) == 1 else (None,)
        if (
            only is not None
            and only.kind == "unit"
            and items(model)[item].unit is None
            and box_of(model, item, None) == item
            and not box_dashed(model, item, None)
        ):
            found[item] = cast("Id[Unit]", only)
    return found


def _joins(links: list[Any]) -> tuple[FieldJoin, ...]:
    """The lifted line of each kind among `links`: the distinct cables, else the link count."""
    kinds: dict[OverviewLinkKind, list[Any]] = {}
    for link in links:
        kinds.setdefault(link.kind, []).append(link)
    out = []
    for kind, held in kinds.items():
        cables = tuple(sorted({link.via for link in held if link.via is not None}))
        out.append(FieldJoin(kind=kind, count=len(cables) or len(held), cables=cables))
    return tuple(sorted(out, key=lambda one: one.kind.value))


def field_fold(model: Model) -> tuple[FieldFold, ...]:
    """The field devices of each unit as one box, "Field devices (n)", in unit box order.

    `devices` are in box text order; `cables` are the cables joining them to the unit.
    """
    by_unit: dict[Id[Unit], list[Id[Item]]] = {}
    for item, unit in field_devices(model).items():
        by_unit.setdefault(unit, []).append(item)
    carried: dict[Id[Unit], list[Any]] = {}
    for link in overview_graph(model).links:
        for unit, held in by_unit.items():
            if {link.a, link.b} & set(held):
                carried.setdefault(unit, []).append(link)
    joins = {unit: _joins(carried.get(unit, [])) for unit in by_unit}
    return tuple(
        FieldFold(
            unit=unit,
            lines=(f"Field devices ({len(held)})",),
            devices=tuple(sorted(held, key=lambda one: box_order(model, one, None))),
            cables=tuple(sorted({c for j in joins[unit] for c in j.cables})),
            joins=joins[unit],
        )
        for unit, held in sorted(by_unit.items(), key=lambda kv: box_order(model, kv[0], None))
    )
