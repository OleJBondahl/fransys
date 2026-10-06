"""Measured widths: the labels' preferred boxes, the keep-outs grown over them, column widths."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping

from fransys_layout.geometry import hull

from ._labelling import slot_box
from .lookups import placed_keepout
from .room import grow_keepout
from .types import ColumnWidth, DrawnFunction, LabelKind

if TYPE_CHECKING:
    from fransys_layout.geometry import Box
    from fransys_model.kernel import AuthoringKey

    from .types import Handle, LabelRequest, PlacedFunction, Profile


def label_boxes(
    drawn: tuple[DrawnFunction, ...], requests: tuple[LabelRequest, ...], profile: Profile
) -> dict[Handle, list[tuple[str, Box]]]:
    """C8(b): per function, its TAG and MARKING labels' preferred boxes, as (slot, box)."""
    owner = {port.port: one.function for one in drawn for port in one.ports}
    geometry = {one.function: one.geometry for one in drawn}
    found: dict[Any, list[tuple[str, Box]]] = {}
    for request in requests:
        if request.kind is LabelKind.TAG:
            function, slot_name = request.subject, "tag"
        elif request.kind is LabelKind.MARKING:
            function, slot_name = owner.get(request.subject), request.slot
        else:
            continue
        slot = (
            next((s for s in geometry[function].slots if s.slot == slot_name), None)
            if function in geometry
            else None
        )
        if slot is not None:
            found.setdefault(function, []).append(
                (slot_name, slot_box(slot, request.text, profile))
            )
    return found


def with_rooms(
    boxes: Mapping[Handle, list[tuple[str, Box]]], rooms: Mapping[Handle, list[tuple[str, Box]]]
) -> dict[Handle, list[tuple[str, Box]]]:
    """S11: per function, `label_boxes`' boxes plus Room's other boxes (`rooms`)."""
    return {f: [*boxes.get(f, ()), *rooms.get(f, ())] for f in boxes.keys() | rooms.keys()}


def grown(
    drawn: tuple[DrawnFunction, ...],
    requests: tuple[LabelRequest, ...],
    profile: Profile,
    *,
    rooms: Mapping[Handle, list[tuple[str, Box]]] | None = None,
) -> tuple[DrawnFunction, ...]:
    """C8(b), S11: the drawn functions with keep-outs grown over their labels' measured boxes."""
    boxes = with_rooms(label_boxes(drawn, requests, profile), rooms or {})
    return tuple(
        replace(
            one, geometry=grow_keepout(one.geometry, [b for _, b in boxes.get(one.function, ())])
        )
        for one in drawn
    )


def placed_widths(
    widths: tuple[ColumnWidth, ...], placed: tuple[PlacedFunction, ...], gap: int
) -> tuple[ColumnWidth, ...]:
    """C21: each column's width, the larger of its estimate and its placed extent plus the gap."""
    held: dict[tuple[AuthoringKey, int, int], list[Box]] = {}
    for one in placed:
        held.setdefault((one.column, one.drawing_set, one.page), []).append(placed_keepout(one))
    actual: dict[AuthoringKey, int] = {}
    for (column, _, _), boxes in held.items():
        actual[column] = max(actual.get(column, 0), hull(boxes).width + gap)
    return tuple(replace(one, width=max(one.width, actual.get(one.column, 0))) for one in widths)
