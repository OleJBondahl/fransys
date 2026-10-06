"""The label boxes, private to `labels` and `sizing`: where a slot label sits.

Everything here is geometry in page coordinates (design/labels.md). `labels` owns the request
order, the obstacles and the findings.
"""

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, Facing, LayoutError, Orientation, text_width, translate

from .types import LabelKind

if TYPE_CHECKING:
    from fransys_layout.geometry import SlotGeometry

    from .types import Handle, LabelRequest, PlacedFunction, Profile


@dataclass(frozen=True, slots=True)
class Home:
    """Where one slot label starts, in page coordinates, with the body it reflects across."""

    owner: Handle
    box: Box
    body: Box
    vertical: bool
    step: int
    drawing_set: int
    page: int


def home(request: LabelRequest, placement: PlacedFunction, profile: Profile) -> Home:
    """The preferred box of one request, and its mirror body; an undefined slot is `LayoutError`."""
    # R6 D1: the terminal-row pseudo-slots are drawn at the symbol's tag slot
    pseudo = ("tag.strip", "tag.point", "tag.pin", "tag.conn", "tag.item")
    wanted = "tag" if request.slot in pseudo else request.slot
    slot = next((one for one in placement.geometry.slots if one.slot == wanted), None)
    if slot is None:
        msg = "a label request names a slot the symbol it is drawn with does not define"
        raise LayoutError(msg)
    box = slot_box(slot, request.text, profile)
    if (
        request.kind is LabelKind.MARKING
        and placement.geometry.orientation is Orientation.R180
        and slot.side in (Facing.E, Facing.W)
    ):
        # R7 A5b: a marking keeps its page side after a flip, beside its own wire
        port_x = next(
            p.at.x for p in placement.geometry.ports if p.name == wanted.removeprefix("marking.")
        )
        box = Box(x=2 * port_x - box.x - box.width, y=box.y, width=box.width, height=box.height)
    if request.slot in pseudo:
        # R6 D1: a terminal-row text is as wide as its text, not the slot, so it fits the pitch
        width = text_width(request.text, height=profile.text_height)
        x = box.x + box.width - width if slot.side is Facing.W else box.x
        box = Box(x=x, y=box.y, width=width, height=box.height)
    if request.level:  # F2: beside the body, level with its centre, as far out as the slot
        body = placement.geometry.body
        gap = abs(slot.at.x - (body.x + body.width // 2))
        x = body.x + body.width + gap if slot.side is Facing.E else body.x - gap - box.width
        y = body.y + (body.height - box.height) // 2
        box = Box(x=x, y=y, width=box.width, height=box.height)
    if request.kind is LabelKind.CROSS_REFERENCE:
        box = translate(box, dx=0, dy=profile.text_height)
    at = placement.at
    found = Home(
        owner=placement.function,
        box=translate(box, dx=at.x, dy=at.y),
        body=translate(placement.geometry.body, dx=at.x, dy=at.y),
        vertical=slot.side in (Facing.E, Facing.W),
        step=profile.text_height,
        drawing_set=placement.drawing_set,
        page=placement.page,
    )
    if request.slot in ("tag.strip", "tag.point", "tag.conn", "tag.item") and found.vertical:
        left = found.box.x + found.box.width // 2 < found.body.x + found.body.width // 2
        if left != (request.slot in ("tag.strip", "tag.conn", "tag.item")):
            found = dataclasses.replace(found, box=_reflected(found))
    return found


def slot_box(slot: SlotGeometry, text: str, profile: Profile) -> Box:
    """One slot's label box, symbol coordinates: near edge fixed, the text grows away."""
    width = text_width(text, height=profile.text_height)
    if slot.side is Facing.E:
        x = slot.at.x
    elif slot.side is Facing.W:
        x = slot.at.x - width
    else:
        x = slot.box.x + slot.box.width // 2 - width // 2
    return Box(x=x, y=slot.box.y, width=width, height=profile.text_height)


def _reflected(where: Home) -> Box:
    """The preferred box mirrored across the body's vertical (E, W) or horizontal centre line."""
    body, box = where.body, where.box
    if where.vertical:
        return Box(
            x=2 * body.x + body.width - box.x - box.width,
            y=box.y,
            width=box.width,
            height=box.height,
        )
    return Box(
        x=box.x,
        y=2 * body.y + body.height - box.y - box.height,
        width=box.width,
        height=box.height,
    )
