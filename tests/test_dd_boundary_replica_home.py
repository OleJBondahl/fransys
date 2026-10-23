"""Layout-0076: a child unit's boundary terminal, wired to a device in another
group, builds ("the records put name one id twice, with different content" before the fix).

Unit `inner` (a child of unit `outer`) holds, all at location FIELD, a strip terminal `T` in group
GA, a relay `Ka` in GA wired to `T`'s outer port (so the chain splits at the group change and `T`
keeps a column of its own), and a relay `K1` in group GB wired to `T`'s inner port on a page of its
own (`break_before`). `T` is a boundary of `inner`; relay `K9` of `outer` is wired to it, so
the black box keeps it (layout-0214). `T` is drawn three times: at home, as a replica
beside `K1` (group GB) in the same drawing set, and as the black box in `outer`'s set.
`replicate_boundaries` took the black box's group from the last column of `T` (the replica beside
`K1`), not from its home, so it inherited GB and two placements in two drawing sets took one key.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _dd_core import designation_of, pages_of, set_of
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity
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
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    outer = d.scope("outer").unit("outer", revision=1, interface="1")
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    inner = outer.scope("in", at=outer.location("BOX", "Box")).unit(
        "inner", revision=1, interface="1"
    )
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    field = inner.location("FIELD", "Field side")
    group_a, group_b = inner.group("GA", "Group A"), inner.group("GB", "Group B")
    terminal = inner.strip("X1", at=field).terminal("DEMO-TB-2.5", group=group_a)
    ka = inner.item("DEMO-RLY-2CO-24", name="Ka", at=field, group=group_a)
    k1 = inner.item("DEMO-RLY-2CO-24", name="K1", at=field, group=group_b)
    wire = inner.wiring(colour="BU", gauge="0.5")
    wire(ka.fn("coil")["A1"], terminal.function["external"])
    wire(k1.fn("coil")["A1"], terminal.inner)
    inner.break_before(group_b)
    inner.boundary(terminal)
    # layout-0214: the parent wires the terminal, so its black box keeps the cell
    k9 = outer.item("DEMO-RLY-2CO-24", name="K9")
    outer.wiring(colour="BU", gauge="0.5")(k9.fn("coil")["A1"], terminal.function["external"])
    return fr.build(parts, d.draft(), layout_trigger_document())


def _terminal_symbols(model) -> list:
    """Every (page id, symbol) drawn for the terminal `X1`: a terminal symbol whose page prints
    an `X1` text."""
    return [
        (page, s)
        for page, drawing in drawn_pages(model).items()
        if any(t.text.startswith("-X1") or "-X1:" in t.text for t in drawing.texts)
        for s in drawing.symbols
        if s.key == "terminal"
    ]


def _outer_pages(model) -> dict:
    """The pages of the drawing sets of unit `outer`, page id -> Drawing."""
    outer = {uid for uid, u in units(model).items() if u.key[-2:] == ("outer", "unit")}
    return {
        page: drawing
        for page, drawing in drawn_pages(model).items()
        if set_of(model, page).unit in outer
    }


def test_a_nested_boundary_terminal_with_a_replica_builds_with_keys_of_their_own() -> None:
    """No exception and no ERROR finding; the terminal stands three times, each placement and
    each tag label under an id and a key of its own."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `for column in homes for
    #     cell` -> `for column in columns for cell` (the black box takes the replica's group)
    #     and write/placements.py, `placements`: drop the `"drawing_set", ...` part of a
    #     replica's extra (the two placements then take one key: a LayoutError from the guard
    #     in write/)
    result = _build()
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    model = result.model
    placed = [s for _, s in _terminal_symbols(model)]
    assert len(placed) == 3
    assert len({s.id for s in placed}) == 3
    tags = [
        t.text
        for drawing in drawn_pages(model).values()
        for t in drawing.texts
        if t.kind == "TAG" and t.text.split(":")[0].endswith("X1")
    ]
    assert len(tags) == 3


def test_the_black_box_in_the_parent_stands_in_the_terminals_home_group() -> None:
    """Model-0220: the black box in `outer`'s set is a copy at K9's pin, so it takes K9's page,
    which holds no group, and not GA, the terminal's home group, nor GB, the group of K1."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `for column in homes for
    #     cell` -> `for column in columns for cell` (the black box takes the replica's group)
    model = _build().model
    pages, nodes = layout_of(model, Page), aspect_nodes(model)
    outer = _outer_pages(model)
    boxes = [page for page, s in _terminal_symbols(model) if page in outer]
    k9_pages = [page for page in pages_of(model, designation_of(model, "K9")) if page in outer]
    assert boxes == k9_pages
    assert len(boxes) == 1
    assert {nodes[g.group].key[-1] for g in pages[boxes[0]].groups} == set()


def test_the_parents_wire_to_the_black_box_terminal_is_a_route_with_no_marker() -> None:
    """In `outer`'s set the conductor K9:A1 - X1 external port is one route on one page, and no
    link marker stands at either of its ports there (a same-page pair before model-0220)."""
    model = _build().model
    outer = _outer_pages(model)
    k9_pages = [p for p in pages_of(model, designation_of(model, "K9")) if p in outer]
    assert len(k9_pages) == 1
    (k9_page,) = k9_pages
    assert len(outer[k9_page].wires) == 1
    assert outer[k9_page].markers == ()
