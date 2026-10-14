"""`page_readability` counts what the lint finds, page by page (readability R11, acceptance A6).

The layout cabinet is laid out; each finding is placed on a page through the model's own
records, and the report's row for that page must hold exactly that many. The cabinet's `discovery`
variant strands two cells (`LONE_CELL`) and both its pages are under half full.
"""

import re
from collections import Counter
from functools import cache
from typing import TYPE_CHECKING

import pytest
from fransys_el import OPTIONS
from layout_cabinet import build_cabinet

from fransys_layout import lay_out_schematic, page_readability
from fransys_layout.lint.codes import LONE_CELL, PAGE_UNDERFILLED, WIRE_OVER_LABEL
from fransys_model.kernel import freeze
from fransys_model.layout import DrawingSet, Page, Route, SymbolPlacement, layout_of

if TYPE_CHECKING:
    from fransys_model.derive import ReadabilityPage
    from fransys_model.kernel import Finding, Model


@cache
def _laid(*, discovery: bool) -> tuple[Model, tuple[Finding, ...]]:
    return lay_out_schematic(freeze(build_cabinet(discovery=discovery)), OPTIONS)


def _printed(model: Model) -> dict:
    """Each page id by its printed `(drawing set, page)` numbers."""
    sets = layout_of(model, DrawingSet)
    return {
        page.id: (sets[page.drawing_set].number, page.number)
        for page in layout_of(model, Page).values()
    }


def _by_page(rows: tuple[ReadabilityPage, ...], field: str) -> dict:
    return {(row.drawing_set, row.number): getattr(row, field) for row in rows}


def _expected_struck(model: Model, findings: tuple[Finding, ...]) -> Counter:
    """`WIRE_OVER_LABEL` findings by the printed page of the route they name."""
    pages = _printed(model)
    routes = layout_of(model, Route).values()
    return Counter(
        pages[route.page]
        for found in findings
        if found.code == WIRE_OVER_LABEL
        for route in routes
        if found.subjects[0] in (route.conductor, route.net)
    )


def _expected_lone(model: Model, findings: tuple[Finding, ...]) -> Counter:
    """`LONE_CELL` findings by the printed page their function stands on."""
    pages = _printed(model)
    placements = layout_of(model, SymbolPlacement).values()
    return Counter(
        pages[place.page]
        for found in findings
        if found.code == LONE_CELL
        for place in placements
        if place.function == found.subjects[0]
    )


@pytest.mark.parametrize("discovery", [False, True], ids=["default", "discovery"])
def test_every_page_row_counts_what_the_findings_count(*, discovery: bool) -> None:
    model, findings = _laid(discovery=discovery)
    rows = page_readability(model, OPTIONS)
    assert rows
    struck, lone = _expected_struck(model, findings), _expected_lone(model, findings)
    assert _by_page(rows, "struck_labels") == {
        page: struck[page] for page in _by_page(rows, "number")
    }
    assert _by_page(rows, "lone_cells") == {page: lone[page] for page in _by_page(rows, "number")}


def test_the_discovery_variant_has_lone_cells_for_the_test_to_count() -> None:
    model, findings = _laid(discovery=True)
    assert sum(_expected_lone(model, findings).values()) == 2
    assert sum(_by_page(page_readability(model, OPTIONS), "lone_cells").values()) == 2


@pytest.mark.parametrize("discovery", [False, True], ids=["default", "discovery"])
def test_a_page_row_prints_the_share_its_page_underfilled_finding_prints(
    *, discovery: bool
) -> None:
    model, findings = _laid(discovery=discovery)
    messages = [f.message for f in findings if f.code == PAGE_UNDERFILLED]
    fill = _by_page(page_readability(model, OPTIONS), "fill_percent")
    under = {page: share for page, share in fill.items() if share < 50}
    assert under
    assert len(messages) == len(under)
    for (drawing_set, number), share in under.items():
        assert any(
            f"covers {share} %" in text and re.search(rf"\+C{drawing_set}p{number}\b", text)
            for text in messages
        ), (drawing_set, number, share)


def test_the_rows_are_in_drawing_set_and_page_order_and_name_printed_numbers() -> None:
    model, _ = _laid(discovery=False)
    rows = page_readability(model, OPTIONS)
    assert [(r.drawing_set, r.number) for r in rows] == sorted(_printed(model).values())
    assert {r.page for r in rows} == set(_printed(model))
