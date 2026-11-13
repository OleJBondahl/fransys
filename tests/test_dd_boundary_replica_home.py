"""Layout-0076: a child unit's boundary terminal, wired to a device in another
group, builds ("the records put name one id twice, with different content" before the fix).

Unit `inner` (a child of unit `outer`) holds, all at location FIELD, a strip terminal `T` in group
"""

from typing import Any

import fransys as fr
import fransys_parts
from _dd_core import designation_of, pages_of, set_of
from _drawn_pages import drawn_pages, markers_in, reads_tag
from _model_build_cover import printed
from fransys_author.design import Design

from fransys_model.layout import Page, layout_of
from fransys_model.vocab.tables import aspect_nodes, units

_PROJECT: dict[str, Any] = {
    "title": "Nested boundary terminal",
    "number": "P-1009",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build():
    """The design of the module docstring; returns the build result."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    outer = d.scope("outer").unit("outer", revision=1, interface="1")
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    inner = outer.scope("in", at=outer.location("BOX", "Box")).unit("inner", revision=1, interface="1")
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    field = inner.location("FIELD", "Field side")
    group_a, group_b = inner.group("GA", "Group A"), inner.group("GB", "Group B")
    terminal = inner.strip("X1", at=field).terminal("DEMO-TB-2.5-TWIN", group=group_a)
    ka = inner.item("DEMO-RLY-2CO-24", name="Ka", at=field, group=group_a)
    k1 = inner.item("DEMO-RLY-2CO-24", name="K1", at=field, group=group_b)
    wire = inner.wiring(colour="BU", gauge="0.5")
    wire(ka.fn("coil")["A1"], terminal.function["external"])
    wire(k1.fn("coil")["A1"], terminal.inner)
    wire(ka.fn("coil")["A2"], k1.fn("coil")["A2"])
    inner.boundary(terminal)
    # layout-0214: the parent wires the terminal, so its black box keeps the cell
    k9 = outer.item("DEMO-RLY-2CO-24", name="K9")
    outer.wiring(colour="BU", gauge="0.5")(k9.fn("coil")["A1"], terminal.function["external"])
    back = outer.strip("X2").terminal("DEMO-TB-2.5")
    outer.wiring(colour="BU", gauge="0.5")(k9.fn("coil")["A2"], back.function["external"])
    return fr.build(parts, *printed(d.draft()))


def _terminal_symbols(model) -> list[Any]:
    """Every (page id, symbol) drawn for the terminal `X1`: a terminal symbol whose point text stands by the run tag `-X1`."""
    return [
        (page, s)
        for page, drawing in drawn_pages(model).items()
        for s in drawing.symbols
        if s.key == "terminal"
        and any(t.owner == s.id and reads_tag(s, drawing, t.text if t.text.startswith("-X1") else f"-X1:{t.text}") for t in drawing.texts)
    ]


def _boundary_wires(drawing, box) -> list[Any]:
    """The wires of `drawing` that touch the body `box` of the boundary terminal's black box."""
    return [w for w in drawing.wires if any(box.x <= x <= box.x + box.w and box.y <= y <= box.y + box.h for x, y in w.points)]


def _outer_pages(model) -> dict[Any, Any]:
    """The pages of the drawing sets of unit `outer`, page id -> Drawing."""
    outer = {uid for uid, u in units(model).items() if u.key[-2:] == ("outer", "unit")}
    return {page: drawing for page, drawing in drawn_pages(model).items() if set_of(model, page).unit in outer}


def test_the_black_box_in_the_parent_stands_in_the_terminals_home_group() -> None:
    """Model-0220: the black box in `outer`'s set is a replica at K9's pin, so it takes K9's page;
    R733: the replica adds its group GA to that page's title, and GB, the group of K1, stays off."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `for column in homes for
    #     cell` -> `for column in columns for cell` (the black box takes the replica's group)
    model = _build().model
    pages, nodes = layout_of(model, Page), aspect_nodes(model)
    outer = _outer_pages(model)
    boxes = [page for page, s in _terminal_symbols(model) if page in outer]
    k9_pages = [page for page in pages_of(model, designation_of(model, "K9")) if page in outer]
    assert boxes == k9_pages
    assert len(boxes) == 1
    assert {nodes[g.group].key[-1] for g in pages[boxes[0]].groups} == {"GA"}


def test_the_parents_wire_to_the_black_box_terminal_is_a_route_with_no_marker() -> None:
    """In `outer`'s set the conductor K9:A1 - X1 external port is one route on one page, and no
    link marker stands at either of its ports there (a same-page pair before model-0220)."""
    model = _build().model
    outer = _outer_pages(model)
    k9_pages = [p for p in pages_of(model, designation_of(model, "K9")) if p in outer]
    assert len(k9_pages) == 1
    (k9_page,) = k9_pages
    (box,) = [s.outline for page, s in _terminal_symbols(model) if page == k9_page]
    assert len({w.net for w in _boundary_wires(outer[k9_page], box)}) == 1
    assert markers_in(outer[k9_page]) == []
