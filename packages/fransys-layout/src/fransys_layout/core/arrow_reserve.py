"""The arrow reserve: a row end that holds a planned arrow keeps `Options.marker.w` free beyond it.

One home for the number. Stage 4 widens a row's size with it; stage 5 widens the row's extent and
the arrow's fan span with it. A row end without an arrow reserves nothing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ref_kind import kind_of
from .values import RefKind

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .values import CutResult, Options, Ref


def reserve(arrows: int, options: Options) -> int:
    """The x kept beyond a row end that holds `arrows` planned arrows."""
    if not arrows:
        return 0
    if options.marker is None:
        msg = "arrow reserve: Options.marker is unset; pass the marker symbol keepout box"
        raise ValueError(msg)
    return (options.link_fit or options.marker)["R0"].w


def arrow_ends(refs: Iterable[Ref], page: int, row: int, fan: str | None = None) -> tuple[int, int]:
    """The planned arrows (of `fan`, or of any fan) at the left and the right end of a row."""
    left = right = 0
    for ref in refs:
        if kind_of(ref) is not RefKind.ARROW or (fan is not None and ref.net != fan):
            continue
        right += (ref.ends[0].page, ref.ends[0].row) == (page, row)
        left += (ref.ends[1].page, ref.ends[1].row) == (page, row)
    return left, right


def card_arrows(cut: CutResult, options: Options) -> dict[str, int]:
    """Each card's box id to the arrow width its planned row keeps free at both ends."""
    cards = {b.id: b.anchor for lst in cut.blocks for b in lst.blocks if b.is_card and b.anchor}
    out: dict[str, int] = {}
    for plan in cut.spec.pages:
        for r, row in enumerate(plan.rows):
            left, right = arrow_ends(cut.spec.reference_plan, plan.page, r)
            for b in row.blocks:
                if b in cards:
                    out[cards[b] or ""] = reserve(left, options) + reserve(right, options)
    return out
