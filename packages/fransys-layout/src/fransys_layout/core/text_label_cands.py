"""Stage 8b candidates: where a designation may stand, most preferred first (layout-0304).

Each box is `Sym.label` in size. KL and KR are the keep-out's slots beside the body, at three
heights per slack; RS is the strip a row-group member's `row_footprint` reserves; BL, TL, BR, TR
are the body's corners moved out by the slack. The order: `Options.corner_order` x `Options.slack`.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from .geometry import rotate_box, shift
from .values import Box

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .outputs import Placed
    from .values import Options, Size, Sym

# corner -> (below the body?, label's left edge on the body's left edge?)
CORNERS = MappingProxyType(
    {"BL": (True, True), "TL": (False, True), "BR": (True, False), "TR": (False, False)}
)
SLOTS = ("KL", "KR")
STRIP = "RS"


def corner_box(body: Box, corner: str, slack: int, size: Size) -> Box:
    """The label box at a body corner, `slack` out from it."""
    if corner not in CORNERS:
        msg = (
            f"unknown label corner {corner!r}: Options.corner_order names one of {sorted(CORNERS)}"
        )
        raise ValueError(msg)
    below, left = CORNERS[corner]
    x = body.x + slack if left else body.x + body.w - slack - size.w
    y = body.y + body.h + slack if below else body.y - size.h - slack
    return Box(x, y, size.w, size.h)


def slot_width(sym: Sym, placed: Placed, corner: str) -> int:
    """The keep-out's width left (KL) or right (KR) of the body, as placed."""
    body, keep = rotate_box(sym.body, placed.orient), rotate_box(sym.keepout, placed.orient)
    return body.x - keep.x if corner == "KL" else keep.x + keep.w - body.x - body.w


def slot_boxes(body: Box, corner: str, slack: int, size: Size) -> list[Box]:
    """Beside the body: centred, above, below; the slack moves each out."""
    x = body.x - size.w if corner == "KL" else body.x + body.w
    tops = (
        body.y + (body.h - size.h) // 2 + slack,
        body.y - size.h - slack,
        body.y + body.h + slack,
    )
    return [Box(x, top, size.w, size.h) for top in tops]


def row_strip(sym: Sym, placed: Placed, size: Size) -> Box | None:
    """The label box in the band `row_footprint` reserves beyond the body, if one fits."""
    if sym.row_footprint is None:
        return None
    body, foot = rotate_box(sym.body, placed.orient), rotate_box(sym.row_footprint, placed.orient)
    bands = (
        Box(foot.x, body.y + body.h, foot.w, foot.y + foot.h - body.y - body.h),
        Box(foot.x, foot.y, foot.w, body.y - foot.y),
        Box(body.x + body.w, foot.y, foot.x + foot.w - body.x - body.w, foot.h),
        Box(foot.x, foot.y, body.x - foot.x, foot.h),
    )
    band = next((b for b in bands if b.w >= size.w and b.h >= size.h), None)
    if band is None:
        return None
    moved = shift(band, placed.body.x - body.x, placed.body.y - body.y)
    return Box(moved.x, moved.y, size.w, size.h)


def side_candidates(sym: Sym, placed: Placed, corner: str, options: Options) -> list[Box]:
    """The keep-out slot candidates of KL or KR; none when the slot is narrower than the label."""
    if slot_width(sym, placed, corner) < sym.label.w:
        return []
    return [b for s in options.slack for b in slot_boxes(placed.body, corner, s, sym.label)]


def candidates(sym: Sym, placed: Placed, options: Options) -> Sequence[tuple[str, Box]]:
    """(corner, box) in preference order; a row-group member's strip stands once, first."""
    strip = row_strip(sym, placed, sym.label)
    out: list[tuple[str, Box]] = []
    for corner in options.corner_order:
        if corner not in SLOTS:
            out += [(corner, corner_box(placed.body, corner, s, sym.label)) for s in options.slack]
        elif strip is None:
            out += [(corner, box) for box in side_candidates(sym, placed, corner, options)]
        elif not any(c == STRIP for c, _ in out):
            out.append((STRIP, strip))
    if not out:
        msg = (
            f"no label candidate for symbol {sym.id!r}: corner_order {options.corner_order} "
            "holds only KL/KR, which need a keep-out slot or a row strip; add BL, TL, BR or TR"
        )
        raise ValueError(msg)
    return out
