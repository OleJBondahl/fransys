"""A probe: a declared net over a boundary function's replica page.

A unit `ua` holds a boundary connector `f` and a peer `g` (both group GA); a top-level connector
`h` (group GT) stands beside them. A declared net `n` joins `f.1`, `g.1` and `h.1`, so its ports'
pages include `f`'s black-box replica page in the top-level set, on a page of its own (a page
break before GA) apart from `h`'s. Pin 2 of `f` is wired to `g.2` inside the unit and to `h.2`
outside it: `f` crosses out of the unit, so it is a valid boundary, and its own-set pin is covered.

Measured on the base: the build has no ERROR finding, and the top-level set carries one marker
pair for the net between `h` and `f`'s replica page. The net group's cuts take the lowest port
on each page and no ruling about a conductor's end pages applies to them: this passes unchanged.

Built through the `fransys` facade from `examples/demo-parts`; read from the page Drawings.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _dd_core import pages_of, set_of
from _dd_core_b import markers
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity
from fransys_model.layout import Page, layout_of

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
    return fr.build(parts, d.draft(), layout_trigger_document())


def _top_level_page_of(model, name: str):
    """The one `Page` of the top-level drawing set that the item `name` is drawn on (a connector
    is one view per wired pin, all on one page here)."""
    (found,) = {page for page in pages_of(model, name) if set_of(model, page).unit is None}
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
    f_page, h_page = _top_level_page_of(model, "f"), _top_level_page_of(model, "h")
    pages = layout_of(model, Page)
    assert pages[f_page].number != pages[h_page].number  # the shape needs the cut: two pages
    on_page = {page: [m for p, m in markers(model) if p == page] for page in (f_page, h_page)}
    assert on_page[h_page]  # the net's owner marker on `h`'s page
    assert on_page[f_page]  # and its user marker on `f`'s replica page
    # g stands in the unit's own set: the net's pair is in the top-level set only
    assert all(set_of(model, page).unit is None for page in on_page)
    assert not set(pages_of(model, "g")) & set(on_page)
