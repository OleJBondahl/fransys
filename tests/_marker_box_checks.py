"""The checks of MARKER-BOX (layout-0406, el-0073): one drawn-marker box in layout, el and the PDF.

`marker_box_facts(build_it)` lays a build out again and returns, per layout marker, the boxes each
home gives it. The rehearsal script runs the same facts on pump-station (reachable only there).
"""

from dataclasses import dataclass
from typing import Any

import pytest
from _direct_case import built_with_unlaid, laid_again
from fransys._link_boxes import link_boxes
from fransys_el import draw_write, lay_out_core

from electrical_symbols import LIBRARY
from fransys_layout.core.geometry import marker_drawn_box
from fransys_layout.symbols import library_symbol, marker_rule
from fransys_model.derive.library_grid import divisions
from fransys_model.kernel import render_id
from fransys_model.layout import LinkMarker, Side, layout_of
lazy from fransys_layout.core.values import Box


@dataclass(frozen=True)
class Facts:
    """One layout marker: the record drawn at its spot with layout's box, and the other homes.

    `matched` is false when no drawn marker at the spot has `marker_drawn_box` as its outline.
    """

    kind: str
    matched: bool
    pdf_ok: bool | None  # the facade's PDF link box equals the old derive.marker_box formula (the outline one gap out)
    fit_ok: bool | None  # `link_fit` at the orient is the rule's box for the fit's own size


def _link_box_from_outline(rec: LinkMarker, outline: Box, gap: int) -> tuple[int, int, int, int]:
    """The PDF link box: the drawn outline one `gap` out of the port along its facing, whatever side the outline grows on (R1595)."""
    dx, dy = {Side.E: (1, 0), Side.W: (-1, 0), Side.N: (0, -1)}.get(rec.facing, (0, 1))
    return outline.x + dx * gap, outline.y + dy * gap, outline.w, outline.h


def _facts(mark, options, pairs, gap: int, boxes) -> Facts:
    kind = str(mark.kind)
    want = marker_drawn_box(mark, options)
    hits = [(rec, sym) for rec, sym in pairs if sym.outline == want]
    if not hits:
        return Facts(kind, matched=False, pdf_ok=None, fit_ok=None)
    rec, sym = hits[0]
    pdf_ok = None
    if rec.via_x is None and rec.box_x is None and rec.stub_extra == 0:
        pdf_ok = boxes[rec.id] == _link_box_from_outline(rec, sym.outline, gap)
    fit_ok = None
    if kind in ("arrow", "tag"):
        fit = options.link_fit[mark.orient]
        along = sym.stretch[0][0] == "y"
        body = marker_rule(library_symbol(LIBRARY, sym.key), sym.orient, (fit.w, fit.h), LIBRARY, along=along)[1]
        fit_ok = body == fit
    return Facts(kind, matched=True, pdf_ok=pdf_ok, fit_ok=fit_ok)


def marker_box_facts(build_it) -> list[Facts]:
    """Every layout marker of the build, laid out again, with what each home says of its box."""
    _, unlaid = built_with_unlaid(build_it)
    sets, opts, final = [], [], []
    real_draw, real_solve = draw_write.draw_set, lay_out_core.solve

    def draw_spy(w):
        sets.append(w)
        final.append(opts[-1])
        return real_draw(w)

    def solve_spy(problem, options, *rest, **kwargs):
        opts.append(options)
        return real_solve(problem, options, *rest, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(draw_write, "draw_set", draw_spy)
        patch.setattr(lay_out_core, "solve", solve_spy)
        laid, drawn = laid_again(unlaid)
    symbols = {s.id: s for d in drawn.values() for s in d.symbols}
    by_spot: dict[tuple[Any, ...], list[Any]] = {}
    for rec in layout_of(laid, LinkMarker).values():
        by_spot.setdefault((rec.page, rec.x, rec.y), []).append((rec, symbols[render_id(rec.id)]))
    gap, boxes = divisions(laid), link_boxes(laid, drawn, LIBRARY)
    return [
        _facts(mark, options, by_spot.get((w.pages[mark.page].id, mark.x, mark.y), ()), gap, boxes)
        for w, options in zip(sets, final, strict=True)
        for mark in w.layout.annotations.markers
    ]
