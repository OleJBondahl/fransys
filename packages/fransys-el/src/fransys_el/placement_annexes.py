"""The designation of each symbol as a core `Annex`: a corner of its body, top left first.

Owner 2026-10-18: a designation stands in a corner of its symbol, "top left by default". The
corners come from `Options.corner_order`, each tried at the corner and one wiring step out, the turned spot on the left after the
second corner, the turned tag centred on the body's height last (TAG-CORNERS, designer R1812, R1831, R1849); the text stage takes
the first one free of every body, wire and earlier annex. A corner
box keeps `label_gap` plus its step beside the wire of the pins on its body edge (`Spot.clear`, R353),
so the step also clears a reference marker that stands on that wire.
"""

from dataclasses import replace
from itertools import chain
from typing import TYPE_CHECKING, Literal

from fransys_layout.core import Annex, Size, Spot

from .placement_kit import ProblemError, refuse

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.core import Options, Orientation, Sym

__all__ = ["label_annexes", "wider_annexes"]

Corner = Literal["TL", "TR", "BL", "BR"]

#: corner -> (below the body?, box's left edge on the body's left edge?)
CORNERS: dict[Corner, tuple[bool, bool]] = {
    "BL": (True, True),
    "TL": (False, True),
    "BR": (True, False),
    "TR": (False, False),
}


def corner_spot(corner: str, slack: int, size: Size, gap: int) -> Spot:
    """The spot at a body corner, `slack` out from it, `gap` clear of the pin wire."""
    known = next((k for k in CORNERS if k == corner), None)
    if known is None:
        fix = f"Options.corner_order names one of {list(CORNERS)}"
        msg = f"unknown label corner {corner!r}"
        raise ProblemError(msg, fix)
    below, left = CORNERS[known]
    dx = slack if left else -slack - size.w
    dy = slack if below else -size.h - slack
    return Spot(corner, known, dx, dy, "down", gap)


def turned_size(label: Size) -> Size:
    """The tag turned a quarter: the thickness by the reading length, the two of its upright size exchanged."""
    return Size(label.h, label.w)


def _ladder(label: Size, options: Options, body_h: int) -> tuple[Spot, ...]:
    """The ladder (LABEL-PLACE 2): two corners, the turned left pair, the rest, then the turned tag centred on the body's height (R1849)."""
    step = options.wiring_grid
    corners = [[corner_spot(c, s, label, options.label_gap + s) for s in (0, step)] for c in options.corner_order]
    turned = turned_size(label)
    if not turned.w:
        return tuple(chain(*corners))
    side = [Spot("TL", "TL", -turned.w, s, "down", options.label_gap, turned=True) for s in (0, step)]
    centred = Spot("TL", "TL", -turned.w, (body_h - turned.h) // 2, "down", options.label_gap, turned=True)
    return (*chain(*corners[:2]), *side, *chain(*corners[2:]), centred)


def _annex(owner: str, sym: Sym, label: Size, options: Options) -> Annex:
    """`owner`'s `Annex` of `label` size, its ladder for each turn of `sym`."""
    turns: dict[Orientation, tuple[Spot, ...]] = {o: _ladder(label, options, v.body.h) for o, v in sym.views.items()}
    return Annex(owner, label, None, turns, turned_size(label))


def _sym_annex(sym: Sym, home: str, options: Options, rise: int) -> Annex:
    """`sym`'s `Annex`; a strip terminal's carries its full-form one as `alone` (STRIP-TAG-ONCE)."""
    annex = _annex(sym.id, sym, (sym.wider[rise - 1] if rise and sym.wider else sym.labels)[home], options)
    return replace(annex, alone=_annex(sym.id, sym, sym.alone[home], options)) if sym.alone else annex


def label_annexes(syms: Sequence[Sym], options: Options, home: str, tags: Mapping[str, Mapping[str, Size]], rise: int = 0) -> tuple[Annex, ...]:
    """One `Annex` per symbol, sized by its tag text as the set of unit `home` prints it ("" the whole model), in the order of `syms`.

    A `rise` of digits more in the where-text page number sizes a symbol by `Sym.wider` (R1883). A strip's first terminal also gives
    the strip's `Annex`, sized by `tags`: the run tag template (STRIP-TAG-ONCE). A strip named like a symbol is refused.
    """
    strips: dict[str, Sym] = {}
    for s in syms:
        if s.row_group is not None and s.row_group in tags:
            strips.setdefault(s.row_group, s)
    if clash := next(iter(strips.keys() & {s.id for s in syms}), None):
        refuse(f"strip {clash}", "a strip is named like a symbol: the run tag and the symbol's tag would share one annex owner", clash)
    return (
        *(_sym_annex(s, home, options, rise) for s in syms),
        *(_annex(g, s, tags[g][home], options) for g, s in strips.items()),
    )


def wider_annexes(syms: Sequence[Sym], options: Options, home: str, tags: Mapping[str, Mapping[str, Size]]) -> tuple[tuple[Annex, ...], ...]:
    """The annexes of `label_annexes` at each rise of the where-text page number's digits the symbols were measured for."""
    return tuple(label_annexes(syms, options, home, tags, rise) for rise in range(1, 1 + max((len(s.wider) for s in syms), default=0)))
