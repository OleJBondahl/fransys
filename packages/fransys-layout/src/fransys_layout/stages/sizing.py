"""Measured widths: the labels' preferred boxes, the keep-outs grown over them, column widths."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping

from ._labelling import slot_box
from .extent import column_extent
from .lookups import owner_of, placed_keepout
from .room import grow_keepout
from .types import ColumnWidth, DrawnFunction, LabelKind

if TYPE_CHECKING:
    from fransys_layout.geometry import Box
    from fransys_model.kernel import AuthoringKey

    from .types import Handle, LabelRequest, PlacedFunction, Profile


def label_boxes(
    drawn: tuple[DrawnFunction, ...], requests: tuple[LabelRequest, ...], profile: Profile
) -> dict[Handle, list[tuple[str, Box]]]:
    """Per function, its TAG and MARKING labels' preferred boxes, as (slot, box)."""
    owner = owner_of(drawn)
    geometry = {one.function: one.geometry for one in drawn}
    found: dict[Any, list[tuple[str, Box]]] = {}
    for request in requests:
        if request.kind is LabelKind.TAG:
            function, slot_name = request.subject, "tag"
        elif request.kind is LabelKind.MARKING:
            function, slot_name = request.function or owner.get(request.subject), request.slot
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
    """Per function, `label_boxes`' boxes plus Room's other boxes (`rooms`)."""
    return {f: [*boxes.get(f, ()), *rooms.get(f, ())] for f in boxes.keys() | rooms.keys()}


def grown(
    drawn: tuple[DrawnFunction, ...],
    requests: tuple[LabelRequest, ...],
    profile: Profile,
    *,
    rooms: Mapping[Handle, list[tuple[str, Box]]] | None = None,
) -> tuple[DrawnFunction, ...]:
    """The drawn functions with keep-outs grown over their labels' measured boxes."""
    boxes = with_rooms(label_boxes(drawn, requests, profile), rooms or {})
    return tuple(
        replace(
            one, geometry=grow_keepout(one.geometry, [b for _, b in boxes.get(one.function, ())])
        )
        for one in drawn
    )


def placed_widths(
    widths: tuple[ColumnWidth, ...],
    placed: tuple[PlacedFunction, ...],
    gap: int,
    extras: Mapping[tuple[int, int, Handle], list[Box]] | None = None,
) -> tuple[ColumnWidth, ...]:
    """Each column's width, the larger of its estimate and its room on the page (layout-0175).

    The room is the pitch to the next column's extent, or the last extent plus the gap; `extras`
    are the label and marker boxes `column_extent` counts with the keep-outs.
    """
    extras = extras or {}
    held: dict[tuple[int, int], dict[AuthoringKey, list[Box]]] = {}
    for one in placed:
        page = held.setdefault((one.drawing_set, one.page), {})
        boxes = page.setdefault(one.column, [])
        boxes.append(placed_keepout(one))
        boxes.extend(extras.get((one.drawing_set, one.page, one.function), ()))
    actual: dict[AuthoringKey, int] = {}
    for page in held.values():
        inks = {key: column_extent(boxes) for key, boxes in page.items()}
        keys = sorted(inks, key=lambda key: inks[key].x)
        for index, key in enumerate(keys):
            ink = inks[key]
            right = inks[keys[index + 1]].x if index + 1 < len(keys) else ink.x + ink.width + gap
            actual[key] = max(actual.get(key, 0), right - ink.x)
    return tuple(replace(one, width=max(one.width, actual.get(one.column, 0))) for one in widths)
