"""DD-CHAIN-LANE (layout-0076): a chain of terminals on one page builds, every conductor drawn.

A strip `X1` of `n` DEMO-TB-2.5 terminals wired inner-to-inner in a chain is one net, so the star
rule draws a branch marker per terminal. The marker of terminal `k` stood in the gap under
terminal `k+1`, across the one exit lane of `k+1`'s inner port; the router took the marker's box as
an obstacle, found no path for that conductor (`ROUTE_FAILED`) and the member check then reported
`CONNECTION_NOT_DRAWN`: both ends are on one page, so nothing is cut. `n` = 3, 4 and 6 built by
luck of the spacing; 5 and 8 did not.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from dataclasses import replace
from itertools import pairwise
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import system_document

from fransys_model.kernel import Origin, Severity, make_id
from fransys_model.layout import (
    LinkMarker,
    Profile,
    Route,
    SheetFormat,
    SymbolPlacement,
    default_profile,
    default_sheet_format,
    layout_of,
)

_PROJECT: dict[str, Any] = {
    "title": "Chain of terminals",
    "number": "P-1008",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build(n: int, *, width_mm: int | None = None):
    """`n` terminals of one strip in one group, wired in a chain; returns the build result.

    With `width_mm`, on an authored sheet whose content is that wide.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    strip = d.strip("X1", at=d.location("C1", "Cabinet"))
    group = d.group("PLC", "PLC")
    terminals = [strip.terminal("DEMO-TB-2.5", group=group) for _ in range(n)]
    wire = d.wiring(colour="BU", gauge="0.5")
    for one, other in pairwise(terminals):
        wire(one.inner, other.inner)
    draft = d.draft()
    if width_mm is not None:
        sheet = replace(
            default_sheet_format(),
            id=make_id(SheetFormat, ("chain", "sheet")),
            key=("chain", "sheet"),
            content_width_mm=width_mm,
            width_mm=width_mm + 20,
        )
        profile = replace(
            default_profile(),
            id=make_id(Profile, ("chain", "profile")),
            key=("chain", "profile"),
            sheet_format=sheet.id,
        )
        draft.extend((sheet, profile), origin=Origin(file=__file__, line=1, note="narrow sheet"))
    return fr.build(parts, draft, system_document())


@pytest.mark.parametrize("n", [3, 4, 5, 6, 8, 12])
def test_a_chain_of_terminals_builds_with_every_conductor_drawn(n: int) -> None:
    """No ERROR finding (`ROUTE_FAILED`, `CONNECTION_NOT_DRAWN`) and wires are drawn: a chain's
    star draws only some conductors as routes and the rest as branches, so the count is not
    asserted, only that the build drew routes at all."""
    # UNDO: stages/marker_lanes.py `_sibling_lanes`: the last line
    #     `return [*lanes, *_foreign_lanes(marker, placed, south=south)]` becomes `return lanes`
    #     (the box then stays across another function's lane, layout-0076)
    result = _build(n)
    errors = [(f.code, f.severity.name) for f in result.findings if f.severity is Severity.ERROR]
    assert errors == []
    assert layout_of(result.model, Route)


@pytest.mark.parametrize("n", [5, 12])
def test_a_chain_of_terminals_stands_in_one_row_on_one_line(n: int) -> None:
    """S20 M12 (ADDENDUM 19 fix 3): the terminals of the chain stand in one row in strip order,
    their links are wires on one line below it, and no link is a reference (no `LinkMarker`)."""
    # UNDO: engines/schematic/engine.py: `all_columns = join_terminal_rows(` ... `)` is removed
    #     (the terminals stack in columns again and their links become references)
    result = _build(n)
    placed = sorted(layout_of(result.model, SymbolPlacement).values(), key=lambda p: p.x)
    assert [p.key[5] for p in placed] == [str(k) for k in range(1, n + 1)]
    assert len({p.y for p in placed}) == 1
    routes = list(layout_of(result.model, Route).values())
    assert len(routes) == n - 1
    runs = {a.y for r in routes for a, b in pairwise(r.points) if a.y == b.y}
    assert len(runs) == 1
    assert runs != {placed[0].y}
    assert not layout_of(result.model, LinkMarker)


def test_a_chain_too_long_for_one_row_stays_drawn_where_its_links_share_a_page() -> None:
    """S20 M12 (ADDENDUM 20): twelve terminals on a sheet 100 mm wide cannot stand in one row, so
    they stack in columns over several pages. A link between two terminals of one page is still
    a drawn route, never a reference pair; only the links a page boundary cuts have markers."""
    # UNDO: stages/terminal_rows.py `join_terminal_rows`: `if not fits(built):` -> `if False:`
    #     (the row is built too wide, so no terminal is left stacked and the page count differs)
    result = _build(12, width_mm=100)
    placed = {p.key[5]: p for p in layout_of(result.model, SymbolPlacement).values()}
    assert len({p.page for p in placed.values()}) > 1
    same_page = sum(placed[str(k)].page == placed[str(k + 1)].page for k in range(1, 12))
    assert same_page > 0
    assert len(layout_of(result.model, Route)) == same_page
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
