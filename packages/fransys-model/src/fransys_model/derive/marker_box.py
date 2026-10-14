"""Where a link marker's box sits: the one rule render draws it by and the PDF links it by (NV2)."""

from dataclasses import replace

from fransys_model.layout import LinkMarker, Side

from .text_width import G_PER_MODULE

__all__ = ["marker_box", "marker_box_origin"]

_STEP = {Side.N: (0, -1), Side.E: (1, 0), Side.S: (0, 1), Side.W: (-1, 0)}


def marker_box_origin(marker: LinkMarker, facing: Side) -> tuple[int, int]:
    """The box's top-left corner in G: one wiring grid out of the port along `facing`.

    The record's own size, pushed out by `stub_extra`; a shared box takes `box_x`.
    """
    w, h = marker.width, marker.height
    match facing:
        case Side.E:
            x, y = marker.x + G_PER_MODULE, marker.y - h // 2
        case Side.W:
            x, y = marker.x - G_PER_MODULE - w, marker.y - h // 2
        case Side.N:
            x, y = marker.x - w // 2, marker.y - G_PER_MODULE - h
        case Side.S:
            x, y = marker.x - w // 2, marker.y + G_PER_MODULE
    dx, dy = _STEP[facing]
    x, y = x + dx * marker.stub_extra, y + dy * marker.stub_extra
    return (x if marker.box_x is None else marker.box_x), y


def marker_box(marker: LinkMarker) -> tuple[int, int, int, int]:
    """The drawn box as `(x, y, width, height)` in G.

    A marker that leaves its port sideways stands its turned box at the end of the branch,
    centred on its shared box if it has one.
    """
    facing = marker.facing
    assert facing is not None  # noqa: S101 - freeze refuses a marker without it
    if marker.via_x is None or marker.via_y is None:
        x, y = marker_box_origin(marker, facing)
    else:
        centre = marker.box_x + marker.width // 2 if marker.box_x is not None else marker.via_x
        straight = replace(marker, x=centre, y=marker.via_y, box_x=None, stub_extra=0)
        x, y = marker_box_origin(straight, facing)
    return x, y, marker.width, marker.height
