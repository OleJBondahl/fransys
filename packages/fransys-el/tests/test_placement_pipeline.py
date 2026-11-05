"""End to end: `build` output through the five landed layout stages (P1-6, el-0002).

Two models run: the demo design and a wide terminal strip. Each builds once for the module. The
distribution board of the corpus runs in `internal/tests/test_placement_pipeline_board.py`.
"""
# WIRE_ROW_UNRESOLVED 12 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

from dataclasses import replace
from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _expected_codes import expect_codes
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import Conventions, build, options
from placement_fixtures import demo_model, kit_for, placed

from electrical_symbols import LIBRARY

if TYPE_CHECKING:
    from fransys_layout.core import Placement
    from fransys_model.kernel import Model

WIDER = "WIDER_THAN_PAGE"


def strip_design(terminals: int) -> fr.Design:
    """A supply and one strip of `terminals` terminals, each wired across the supply."""
    # The short is kept on purpose: only a terminal between two supply nets places as the one-row fan (layout-0309, WIDER_THAN_PAGE).
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", terminals)
    with d.function("FEED", "Strip feed"):
        for n in range(1, terminals + 1):
            d.series(dc.plus, x1[n], dc.minus, wire=(BU, 0.75))
    return d


def strip_model(terminals: int) -> Model:
    """The strip model; its deliberate short is asserted here, so the sweep sees it asserted (R1712)."""
    built = fr.build(strip_design(terminals))
    expect_codes(built, "NET_SHORTED", "NET_POTENTIAL_CONFLICT")  # the short forms the one-row fan (R1745, KI-657)
    codes = [f.code for f in built.findings]
    assert (codes.count("NET_SHORTED"), codes.count("NET_POTENTIAL_CONFLICT")) == (1, 1)
    return built.model


def test_the_strip_model_gives_exactly_one_short_and_one_potential_conflict() -> None:
    """R1736.2: the deliberate short of the strip fixture is asserted, not left anchored."""
    built = fr.build(strip_design(40))
    expect_codes(built, "NET_SHORTED", "NET_POTENTIAL_CONFLICT")
    codes = [f.code for f in built.findings]
    assert codes.count("NET_SHORTED") == 1
    assert codes.count("NET_POTENTIAL_CONFLICT") == 1


@pytest.fixture(scope="module")
def demo() -> Placement:
    model = demo_model()
    return placed(model, kit_for(model), house())


@pytest.fixture(scope="module")
def wide() -> Placement:
    model = strip_model(40)
    return placed(model, kit_for(model), house())


def test_the_demo_model_places_without_a_wider_than_page_finding(demo: Placement) -> None:
    assert demo.pages
    assert [f for f in demo.findings if f.code == WIDER] == []


def test_the_same_model_gives_the_same_placement_twice(demo: Placement) -> None:
    model = demo_model()
    assert placed(model, kit_for(model), house()) == demo


def strip_group(model: Model, conventions: Conventions) -> str:
    """The one row group the problem holds: the strip's."""
    prob, _ = build(model, kit_for(model), conventions, LIBRARY)
    groups = {s.row_group for s in prob.symbols if s.row_group}
    assert len(groups) == 1
    return groups.pop()


def test_a_wide_strip_wraps_and_levels_its_row_group_per_page_row(wide: Placement) -> None:
    """layout-0309: the 40-member strip wraps into rows, so no WIDER_THAN_PAGE.

    Its row group levels per page row (row_group_aligns), so the wrap drops nothing.
    """
    strip_group(strip_model(40), house())
    assert wide.findings == ()
    assert len(wide.pages[0].rows) > 1


def test_a_strip_wider_than_the_area_gives_exactly_one_wider_than_page_when_not_wrapped() -> None:
    model = strip_model(40)
    conventions = replace(house(), options=replace(options(house(), LIBRARY), wrap_wide_fans=False))
    assert [f.code for f in placed(model, kit_for(model), conventions).findings] == [WIDER]
