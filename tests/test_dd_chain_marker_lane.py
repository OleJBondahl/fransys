"""Layout-0076: a chain of terminals on one page builds, every conductor drawn.

A strip `X1` of `n` DEMO-TB-2.5 terminals wired inner-to-inner in a chain is one net, so the star
rule draws a branch marker per terminal. The marker of terminal `k` stood in the gap under
"""

from itertools import pairwise
from typing import Any

import fransys as fr
import fransys_parts
import pytest
from _drawn_pages import drawn_pages, markers_in
from _model_build_cover import cabinet_document, layout_trigger_document
from _no_power_net import assert_no_power_net
from fransys_author.design import Design

from fransys_model.derive.drawing_text import marker_text
from fransys_model.derive.facts.house_settings import reference_text_of
from fransys_model.kernel import Severity
from fransys_model.layout import LinkMarker, layout_of

_PROJECT: dict[str, Any] = {
    "title": "Chain of terminals",
    "number": "P-1008",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build(n: int):
    """`n` terminals of one strip in one group, wired in a chain; returns the build result."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    cabinet = d.location("C1", "Cabinet")
    strip = d.strip("X1", at=cabinet)
    group = d.group("PLC", "PLC")
    terminals = [strip.terminal("DEMO-TB-2.5-TWIN", group=group) for _ in range(n)]
    wire = d.wiring(colour="BU", gauge="0.5")
    for one, other in pairwise(terminals):
        wire(one.inner, other.inner)
    draft = d.draft()
    return fr.build(parts, draft, layout_trigger_document(), cabinet_document(cabinet))


def _terminal_tags(model) -> dict[str, tuple[Any, ...]]:
    """The strip index of each terminal (the tag's last part) -> (page id, tag box, symbol)."""
    found = {}
    for page, drawing in drawn_pages(model).items():
        tags = [t for t in drawing.texts if t.kind == "TAG" and t.text.startswith("-X1:")]
        terminals = [s for s in drawing.symbols if s.key == "terminal"]
        for tag in tags:
            found[tag.text.rsplit(":", 1)[1]] = (page, tag.box, terminals)
    return found


def _wires(model) -> list[Any]:
    return [w for drawing in drawn_pages(model).values() for w in drawing.wires]


@pytest.mark.parametrize("n", [3, 4, 5, 6, 8, 12])
def test_a_chain_of_terminals_builds_with_every_conductor_drawn(n: int) -> None:
    """No ERROR finding (`CONNECTION_NOT_DRAWN`) and wires are drawn: a chain's
    star draws only some conductors as routes and the rest as branches, so the count is not
    asserted, only that the build drew routes at all."""
    # UNDO: stages/marker_lanes.py `_sibling_lanes`: the last line
    #     `return [*lanes, *_foreign_lanes(marker, placed, south=south)]` becomes `return lanes`
    #     (the box then stays across another function's lane, layout-0076)
    result = _build(n)
    errors = [(f.code, f.severity.name) for f in result.findings if f.severity is Severity.ERROR]
    assert errors == []
    assert _wires(result.model)


@pytest.mark.rule("BUNDLE")
@pytest.mark.parametrize("n", [5, 12])
def test_a_chain_of_terminals_stands_in_one_row_on_one_line(n: int) -> None:
    """The terminals stand in one row in strip order; the net is one trunk on one line below it,
    a drop per terminal, a dot at each inner drop, no marker (ROUTING, BUNDLE, R467)."""
    # UNDO: engines/schematic/engine.py: `all_columns = join_terminal_rows(` ... `)` is removed
    #     (the terminals stack in columns again and their links become references)
    model = _build(n).model
    assert_no_power_net(model)
    tags = _terminal_tags(model)
    placed = sorted(tags.items(), key=lambda item: item[1][1].x)
    assert [k for k, _ in placed] == [str(k) for k in range(1, n + 1)]
    terminals = [s for drawing in drawn_pages(model).values() for s in drawing.symbols if s.key == "terminal"]
    assert len({s.y for s in terminals}) == 1
    routes = _wires(model)
    assert len(routes) == n + 1  # one trunk and a drop per terminal
    dots = [s for d in drawn_pages(model).values() for s in d.symbols if s.key == "junction-dot"]
    assert len(dots) == n - 2
    runs = {a[1] for r in routes for a, b in pairwise(r.points) if a[1] == b[1]}
    assert len(runs) == 1
    assert runs != {terminals[0].y}
    assert not [m for drawing in drawn_pages(model).values() for m in markers_in(drawing)]


def test_a_chain_split_over_two_pages_draws_every_terminal_once_and_marks_the_link_on_both() -> None:
    """240 twin terminals on the default sheet fill two pages (a twin draws narrower, so 160 fit one):
    each is drawn once and the link across the break is a cross-page marker pair,
    one on each page, its text the `[reference]` home's cross-page form."""
    # UNDO: the link marker of one page is dropped (the chain then breaks with no reference on that page)
    result = _build(240)
    model = result.model
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    pages = drawn_pages(model)
    tags = [t.text for d in pages.values() for t in d.texts if t.kind == "TAG" and t.text.startswith("-X1:")]
    assert sorted(tags) == sorted(f"-X1:{k}" for k in range(1, 241))
    assert len(pages) == 2
    markers = layout_of(model, LinkMarker)
    cross = [m for m in markers.values() if markers[m.partner].page != m.page]
    assert len(cross) == 2
    assert {m.page for m in cross} == set(pages)
    refs = reference_text_of(model)
    assert all(refs.page_prefix in marker_text(model, m) for m in cross)
