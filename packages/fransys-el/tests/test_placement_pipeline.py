"""End to end: `build` output through the five landed layout stages (P1-6, el-0002).

Two models run: the demo design and a wide terminal strip. Each builds once for the module. The
distribution board of the corpus runs in `internal/tests/test_placement_pipeline_board.py`.
"""

from dataclasses import replace
from typing import TYPE_CHECKING

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_el import Conventions, build, options
from placement_fixtures import demo_model, kit_for, placed

if TYPE_CHECKING:
    from fransys_layout.core import Placement
    from fransys_model.kernel import Model

WIDER = "WIDER_THAN_PAGE"


def strip_model(terminals: int) -> Model:
    """A supply and one strip of `terminals` terminals, each wired across the supply."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", terminals)
    with d.function("FEED", "Strip feed"):
        for n in range(1, terminals + 1):
            d.series(dc.plus, x1[n], dc.minus, wire=(BU, 0.75))
    return fr.build(d).model


@pytest.fixture(scope="module")
def demo() -> Placement:
    model = demo_model()
    return placed(model, kit_for(model), Conventions())


@pytest.fixture(scope="module")
def wide() -> Placement:
    model = strip_model(40)
    return placed(model, kit_for(model), Conventions())


def test_the_demo_model_places_without_a_wider_than_page_finding(demo: Placement) -> None:
    assert demo.pages
    assert [f for f in demo.findings if f.code == WIDER] == []


def test_the_same_model_gives_the_same_placement_twice(demo: Placement) -> None:
    model = demo_model()
    assert placed(model, kit_for(model), Conventions()) == demo


def strip_group(model: Model, conventions: Conventions) -> str:
    """The one row group the problem holds: the strip's."""
    prob, _ = build(model, kit_for(model), conventions)
    groups = {s.row_group for s in prob.symbols if s.row_group}
    assert len(groups) == 1
    return groups.pop()


def test_a_wide_strip_wraps_and_drops_only_its_row_group_alignment(wide: Placement) -> None:
    """layout-0309: the 40-member strip wraps into rows, so no WIDER_THAN_PAGE.

    Its row group asks one y for all members at a column end (spec P6, row_group_aligns),
    which rows at different heights cannot give: the one finding is ALIGN_DROPPED for that group.
    """
    group = strip_group(strip_model(40), Conventions())
    assert [(f.code, f.subject) for f in wide.findings] == [("ALIGN_DROPPED", group)]
    assert len(wide.pages[0].rows) > 1


def test_a_strip_wider_than_the_area_gives_exactly_one_wider_than_page_when_not_wrapped() -> None:
    model = strip_model(40)
    conventions = Conventions(options=replace(options(Conventions()), wrap_wide_fans=False))
    assert [f.code for f in placed(model, kit_for(model), conventions).findings] == [WIDER]
