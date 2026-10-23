"""`placement_series.within`: a scope keeps the part of each series it draws (SP3)."""

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_el import build, house_conventions, options, symbol_kit
from fransys_el.placement_series import within
from fransys_el.placement_skips import NOT_SERIES_PARALLEL

from electrical_symbols import LIBRARY
from fransys_layout.core import Parallel, Series, solve

_TREE = Series(("S1", Parallel(("S2", Series(("S3", "S4")))), "H1"))


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_scope_keeps_its_own_leaves_in_the_tree_shape() -> None:
    """Catches a series dropped whole when one leaf is in another scope."""
    assert within(_TREE, {"S1", "S3", "S4", "H1"}) == Series(("S1", "S3", "S4", "H1"))
    assert within(_TREE, {"S2", "S3", "S4"}) == Series((Parallel(("S2", Series(("S3", "S4")))),))


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_scope_with_one_leaf_of_a_series_keeps_none_of_it() -> None:
    """Catches a series of one symbol kept: it orders nothing."""
    assert within(_TREE, {"S1", "K9"}) is None
    assert within(_TREE, set()) is None


def _bridge_model() -> fr.Model:
    """A Wheatstone shape: S4 joins the middles of S2-S5 and S3-S6, all into H1."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("G", "Group"):
        s = {n: d.device(f"S{n}", "DEMO-PB-NO", place="L0").sw for n in "123456"}
        h1 = d.device("H1", "DEMO-LAMP-24", place="L0").lamp
        pairs = (("1", "2"), ("1", "3"), ("2", "4"), ("2", "5"), ("4", "3"), ("3", "6"))
        for a, b in pairs:
            d.detail.wire(s[a]["B"], s[b]["A"], wire=(BU, 0.5))
        for a in ("5", "6"):
            d.detail.wire(s[a]["B"], h1["1"], wire=(BU, 0.5))
    return fr.build(d).model


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_bridge_in_a_build_is_skipped_once_and_its_symbols_stay_drawn() -> None:
    """Catches the bridge's warning dropped on the way out of el, or a bridge symbol left out."""
    model = _bridge_model()
    problem, skipped = build(
        model, symbol_kit(model, LIBRARY), house_conventions(fr.settings().layout, LIBRARY), LIBRARY
    )
    bridges = [s for s in skipped if s.reason == NOT_SERIES_PARALLEL]
    assert len(bridges) == 1
    assert len(bridges[0].more) == len(problem.symbols) - 1 == 6
    assert problem.facts.series == ()


def _control_model() -> fr.Model:
    """`d.series(s1, d.parallel(s2, d.series(s3, s4)), h1)` as wires: the spec's control circuit."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("G", "Group"):
        s = {n: d.device(f"S{n}", "DEMO-PB-NO", place="L0").sw for n in "1234"}
        h1 = d.device("H1", "DEMO-LAMP-24", place="L0").lamp
        pairs = ((s["1"]["B"], s["2"]["A"]), (s["1"]["B"], s["3"]["A"]), (s["3"]["B"], s["4"]["A"]))
        for a, b in (*pairs, (s["2"]["B"], h1["1"]), (s["4"]["B"], h1["1"])):
            d.detail.wire(a, b, wire=(BU, 0.5))
    return fr.build(d).model


@pytest.mark.rule("SERIES-PARALLEL")
def test_a_nested_control_circuit_stands_as_one_column_source_first() -> None:
    """Acceptance 2: S2 in a lane beside S3 and S4, S1 above them, H1 below both."""
    model = _control_model()
    problem, _ = build(
        model, symbol_kit(model, LIBRARY), house_conventions(fr.settings().layout, LIBRARY), LIBRARY
    )
    laid = solve(problem, options(house_conventions(fr.settings().layout, LIBRARY), LIBRARY))
    at = {p.sym.split(" ")[0]: (p.x, p.y) for page in laid.placement.pages for p in page.placed}
    assert at["S1"][0] == at["S3"][0] == at["S4"][0] == at["H1"][0]
    assert at["S2"][0] > at["S3"][0]
    assert at["S1"][1] < at["S2"][1] == at["S3"][1] < at["S4"][1] < at["H1"][1]
