"""Every designation stands in a corner of its symbol, top left by default (owner 2026-10-18).

"designations have four positions, one in each corner of the symbol" and "stanard position is top
left corner, above the box, some distance from the wire", for every symbol. The card and lamps
"""

import fransys as fr
import pytest
from _card_case import card_case_drafts, lamps_drafts
from conventions_fixtures import house
from fransys_el import build, symbol_kit
from fransys_el.kit_keys import tag_of
from fransys_el.placement_ids import symbol_key
from fransys_el.placement_options import options

from electrical_symbols import LIBRARY
from fransys_layout.core import Box, solve
from fransys_layout.core.annex import place_labels, spot_box
from fransys_layout.core.geometry import overlaps

CORNERS = {"TL", "BL", "BR", "TR"}
# The designations that do not stand top left, by their tag: the content box leaves no room at
# the page's left edge for a label beside the wire of a pin that near it.
FALLBACKS = {
    "card16": {},
    "lamps": {},
}


@pytest.fixture(scope="module", params=["card16", "lamps"])
def page(request):
    drafts = card_case_drafts(16) if request.param == "card16" else lamps_drafts()
    model = fr.build(*drafts).model
    conventions = house()
    kit = symbol_kit(model, LIBRARY)
    problem, _ = build(model, kit, conventions, LIBRARY)
    core = solve(problem, options(conventions, LIBRARY))
    names = {symbol_key(model, f): tag_of(model, f) for f in kit}
    return request.param, core, problem, names


def test_every_designation_that_has_room_stands_top_left_and_each_fallback_is_named(page) -> None:
    name, core, _, names = page
    fallbacks = {names[x.owner]: x.spot for x in core.annotations.annexes if x.spot != "TL"}
    assert len(core.annotations.annexes) > 0
    assert fallbacks == FALLBACKS[name]


def test_every_designation_stands_in_one_of_its_symbols_four_corners(page) -> None:
    _, core, _, _ = page
    assert {x.spot for x in core.annotations.annexes} <= CORNERS


def _zone(body: Box, corner: str, label: Box) -> Box:
    """The corner zone: the body's half on that side and one label width past its edge."""
    reach = 8  # the ladder's one step out (LABEL-PLACE)
    x = body.x - label.w if corner[1] == "L" else body.x + body.w // 2
    y = body.y + body.h if corner[0] == "B" else body.y - label.h - reach
    return Box(x, y, body.w // 2 + label.w, label.h + reach)


def _touches(a: Box, b: Box) -> bool:
    return a.x <= b.x + b.w and b.x <= a.x + a.w and a.y <= b.y + b.h and b.y <= a.y + a.h


def test_each_designations_box_touches_its_symbols_corner_zone(page) -> None:
    _, core, _, _ = page
    bodies = {p.sym: p.body for pg in core.placement.pages for p in pg.placed}
    for x in core.annotations.annexes:
        assert _touches(x.box, _zone(bodies[x.owner], x.spot, x.box)), (x.owner, x.spot)


def test_each_annex_passes_the_ladder_a_corner_and_one_step_out_in_the_order_tl_bl_tr_br(page) -> None:
    """LABEL-PLACE 2: ten spots (a turned pair left of the body after BL), the turned one centred on the body last (R1849)."""
    _, _, problem, _ = page
    step = house().options.wiring_grid
    assert problem.annexes
    for annex in problem.annexes:
        for spots in annex.spots.values():
            assert [s.name for s in spots] == [*(c for c in ("TL", "BL", "TL", "TR", "BR") for _ in (0, 1)), "TL"]
            assert [s.turned for s in spots] == [i in (4, 5, 10) for i in range(11)]
            assert [s.clear - spots[0].clear for s in spots[:2]] == [0, step]


def test_every_designation_stands_inside_the_content_box(page) -> None:
    _, core, problem, _ = page
    for x in core.annotations.annexes:
        assert x.box.x >= 0
        assert x.box.y >= 0
        assert x.box.x + x.box.w <= problem.area.w
        assert x.box.y + x.box.h <= problem.area.h


def _lines(core) -> list[tuple[str, tuple[int, int, int, int]]]:
    """Every drawn line as (owner, (x0, y0, x1, y1)): wire segments and body outline edges."""
    out: list[tuple[str, tuple[int, int, int, int]]] = []
    for pr in core.routes.pages:
        for w in pr.wires:
            out += [("", (*a, *b)) for a, b in zip(w.points, w.points[1:], strict=False)]
    for pg in core.placement.pages:
        for p in pg.placed:
            b = p.body
            edges = ((b.x, b.y, b.x + b.w, b.y), (b.x, b.y + b.h, b.x + b.w, b.y + b.h))
            sides = ((b.x, b.y, b.x, b.y + b.h), (b.x + b.w, b.y, b.x + b.w, b.y + b.h))
            out += [(p.sym, e) for e in edges + sides]
    return out


def _meets(box: Box, line: tuple[int, int, int, int]) -> bool:
    x0, y0, x1, y1 = line
    return min(x0, x1) < box.x + box.w and box.x < max(x0, x1) and (min(y0, y1) < box.y + box.h and box.y < max(y0, y1))


def test_no_designation_box_touches_a_drawn_line_but_its_own_symbols_body(page) -> None:
    _, core, _, _ = page
    lines = _lines(core)
    assert len(lines) > 0
    assert len(core.annotations.annexes) > 0
    for x in core.annotations.annexes:
        hit = [line for owner, line in lines if owner != x.owner and _meets(x.box, line)]
        assert hit == [], (x.owner, x.spot, hit)


def _pin_down(box: Box, keep: Box) -> Box:
    """A small wall inside `box` and clear of `keep`, so `box` is blocked and `keep` is not."""
    spots = [Box(x, y, 3, 3) for x in (box.x + 1, box.x + box.w - 4) for y in (box.y + 1, box.y + box.h - 4)]
    return next(s for s in spots if not overlaps(s, keep))


def test_a_tag_stands_at_the_centred_turned_rung_when_the_ten_before_it_are_blocked(page) -> None:
    """R1849: rung 11 is the turned tag centred on the body's height on its left; with every other box walled it is where the tag stands."""
    _, core, problem, _ = page
    placed = {p.sym: p for pg in core.placement.pages for p in pg.placed}
    annex = max((a for a in problem.annexes if a.turned is not None and a.turned.w), key=lambda a: placed[a.owner].body.h)
    here = placed[annex.owner]
    boxes = [spot_box(here, annex.turned if s.turned else annex.size, s, 0) for s in annex.spots[here.orient]]
    walls = [_pin_down(b, boxes[-1]) for b in boxes[:-1]]
    (label,), found, _ = place_labels([annex], {annex.owner: here}, ((), walls), (1, problem.area, 0, 2))
    assert (label.spot, label.turned, label.box) == ("TL", True, boxes[-1])
    assert found == []
    assert label.box.x + label.box.w <= here.body.x
    assert abs((label.box.y + label.box.h / 2) - (here.body.y + here.body.h / 2)) <= 1
