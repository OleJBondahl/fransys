"""CUT-END part 3 probe: a declared net over a boundary function's replica page.

A unit `ua` holds a boundary connector `f` and a peer `g` (both group GA); a top-level connector
`h` (group GT) stands beside them. A declared net `n` joins `f.1`, `g.1` and `h.1`, so its ports'
pages include `f`'s black-box replica page in the top-level set, on a page of its own (a page
break before GA) apart from `h`'s. Pin 2 of `f` is wired to `g.2` inside the unit and to `h.2`
outside it: `f` crosses out of the unit, so it is a valid boundary, and its own-set pin is covered.

Measured on the base: the build has no ERROR finding, and the top-level set carries one marker
pair for the net between `h` and `f`'s replica page. The net group's cuts take the lowest port
on each page and no ruling about a conductor's end pages applies to them: this passes unchanged.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.kernel import Severity
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    MarkerSide,
    Page,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, ports

_PROJECT: dict[str, Any] = {
    "title": "Cut end net group",
    "number": "P-1012",
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
    at = d.location("C1", "Cabinet")
    ua = d.scope("ua").unit("ua", revision=1, interface="1")
    ua.revision(1, date="2026-01-01", text="First release", created="XX")
    group_a, group_t = ua.group("GA", "Group A"), d.group("GT", "Group T")
    f = ua.item("DEMO-CONN-2P", name="f", tag="X1", at=at, group=group_a)
    g = ua.item("DEMO-CONN-2P", name="g", tag="X2", at=at, group=group_a)
    ua.boundary(f)
    h = d.item("DEMO-CONN-2P", name="h", tag="X3", at=at, group=group_t)
    wire = d.wiring(colour="BU", gauge="0.5")
    wire(f["2"], g["2"])
    wire(f["2"], h["2"])
    d.net("n", f["1"], g["1"], h["1"])
    d.break_before(group_a)
    return fr.build(parts, d.draft(), system_document())


def _pin_one(model, name: str):
    """The id of pin 1 of the connector function `name` (its one `x1` function)."""
    (function,) = (f.id for f in functions(model).values() if f.key[-3:] == (name, "fn", "x1"))
    (port,) = (p.id for p in ports(model).values() if p.function == function and p.name == "1")
    return port


def _top_level_page_of(model, port):
    """The one `Page` of the top-level drawing set that `port`'s function stands on (a connector
    is one view per wired pin, all on one page here)."""
    function = ports(model)[port].function
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    (found,) = {
        pages[p.page]
        for p in layout_of(model, SymbolPlacement).values()
        if p.function == function and sets[pages[p.page].drawing_set].unit is None
    }
    return found


def test_a_net_over_a_boundary_functions_replica_page_builds_and_is_cut_there() -> None:
    """Base: passes ("passes unchanged"). 0 ERROR; the net's pair stands in the top-level set on
    `h`'s page and on `f`'s replica page, naming each other."""
    # UNDO: fransys_layout/stages/references/cuts.py `_cuts`, the
    #   net-group loop: `pairwise(pages)` -> `pairwise(pages[:1])` (no cut
    #   of a group at all; the pair on `f`'s page is gone)
    result = _build()
    model = result.model
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    f1, g1, h1 = (_pin_one(model, name) for name in ("f", "g", "h"))
    f_page, h_page = _top_level_page_of(model, f1), _top_level_page_of(model, h1)
    assert f_page.number != h_page.number  # the shape needs the cut: two pages, one replica
    sets = layout_of(model, DrawingSet)
    pair = [
        m
        for m in layout_of(model, LinkMarker).values()
        if m.port in {f1, h1}
        and m.star is None
        and sets[layout_of(model, Page)[m.page].drawing_set].unit is None
    ]
    owner, user = sorted(pair, key=lambda m: m.side is MarkerSide.USER)
    assert (owner.port, owner.page) == (h1, h_page.id)
    assert (user.port, user.page) == (f1, f_page.id)
    assert (owner.partner, user.partner) == (user.id, owner.id)
    assert g1 not in {m.port for m in pair}
