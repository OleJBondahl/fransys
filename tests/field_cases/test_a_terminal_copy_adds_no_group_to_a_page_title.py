"""A bulkhead strip fed from a unit is drawn as a copy on the page of a load at another place; its group has its devices on another page.
The bug: the load page title named the strip's group, which draws nothing else there. Fixed by layout-0605 (a page rule in the core's group step).
One build, about 10 s: 150 chained lamps are needed to force a second page (WORKING-RULES shared-build rule)."""

from itertools import pairwise
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.derive import page_title
from fransys_model.layout import Page, layout_of


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Io:
    with u.function("CTL", "Controller"):
        x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=(1, 2))
        k1 = u.device("K1", "DEMO-LAMP-24")
        u.series(x1[1].inner, k1.lamp["1"], wire=(BU, 0.5))
        u.series(x1[2].inner, k1.lamp["2"], wire=(BU, 0.5))
    return _Io(x1)


def _titles() -> list[str]:
    d = fr.design("demo_parts", place="FIELD")
    d.location("FIELD", "Field")
    d.location("B", "Bee")
    cab = d.add(_cab, "N", place=None)
    with d.function("BH", "Bulkhead"):
        x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
        p1 = d.device("P1", "DEMO-LAMP-24")
        d.series(cab.X1[1].outer, p1.lamp["1"], wire=(BU, 0.5))
        d.series(p1.lamp["2"], x2[1].inner, wire=(BU, 0.5))
    with d.function("LD", "Load"):
        lamps = [d.device(f"K{i}", "DEMO-LAMP-24", place="B") for i in range(2, 150)]
    with d.function("BH", "Bulkhead"):
        tail = d.device("P3", "DEMO-LAMP-24", place="B")
    d.series(x2[1].outer, lamps[0].lamp["1"], wire=(BU, 0.5))
    for a, b in pairwise(lamps):
        d.series(a.lamp["2"], b.lamp["1"], wire=(BU, 0.5))
    d.series(lamps[-1].lamp["2"], tail.lamp["1"], wire=(BU, 0.5))
    d.series(tail.lamp["2"], cab.X1[2].outer, wire=(BU, 0.5))
    model = fr.build(d, unit_document("demo-cab")).model
    return [page_title(model, page) for page in layout_of(model, Page).values()]


@pytest.mark.rule("PAGE-TITLE")
def test_the_page_that_draws_only_a_strip_copy_of_a_group_is_not_titled_by_it() -> None:
    """Page 1 of the load place draws the strip copy and loads; the strip's group has its device on page 2."""
    titles = _titles()
    assert "Bulkhead, Load" not in titles
    assert "Load" in titles


# TEXT_HIDES_TEXT: a falling stock of this file's builds, KI-1133 (R2647, TEXT-WIRE P0).
