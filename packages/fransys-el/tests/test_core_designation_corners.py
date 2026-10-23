"""Every designation stands in a corner of its symbol, top left by default (owner 2026-10-18).

"designations have four positions, one in each corner of the symbol" and "stanard position is top
left corner, above the box, some distance from the wire", for every symbol. The card and lamps
pages are built once each; the three card fallbacks stand where the content box leaves no room.
"""

import sys
import tempfile
from pathlib import Path

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import build, options, symbol_kit
from fransys_el.kit_keys import tag_of
from fransys_el.placement_ids import symbol_key

from electrical_symbols import LIBRARY
from fransys_layout.core import Box, solve

sys.path.append(str(Path(__file__).parents[3] / "tests"))
from _card_case import card_case_drafts

CORNERS = {"TL", "BL", "BR", "TR"}
# The designations that do not stand top left, by their tag: the content box leaves no room at
# the page's left edge for a label beside the wire of a pin that near it.
FALLBACKS = {
    "card16": {"-K9": "BL"} | {f"-K{n}": "BL" for n in range(10, 17)},
    "lamps": {},
}


def _lamps() -> tuple:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    first, second = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    d.detail.wire(first.coil["A2"], second.coil["A1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)


@pytest.fixture(scope="module", params=["card16", "lamps"])
def page(request):
    drafts = card_case_drafts(16) if request.param == "card16" else _lamps()
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
    reach = 16  # the largest Options.slack
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


def test_every_designation_stands_inside_the_content_box(page) -> None:
    _, core, problem, _ = page
    for x in core.annotations.annexes:
        assert x.box.x >= 0
        assert x.box.y >= 0
        assert x.box.x + x.box.w <= problem.area.w
        assert x.box.y + x.box.h <= problem.area.h


def _lines(core) -> list[tuple[str, tuple[int, int, int, int]]]:
    """Every drawn line as (owner, (x0, y0, x1, y1)): wire segments and body outline edges."""
    out = []
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
    return (
        min(x0, x1) <= box.x + box.w
        and box.x <= max(x0, x1)
        and (min(y0, y1) <= box.y + box.h and box.y <= max(y0, y1))
    )


def test_no_designation_box_touches_a_drawn_line_but_its_own_symbols_body(page) -> None:
    _, core, _, _ = page
    lines = _lines(core)
    assert len(lines) > 0
    assert len(core.annotations.annexes) > 0
    for x in core.annotations.annexes:
        hit = [line for owner, line in lines if owner != x.owner and _meets(x.box, line)]
        assert hit == [], (x.owner, x.spot, hit)
