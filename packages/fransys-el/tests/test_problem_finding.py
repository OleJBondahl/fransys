"""`problem_finding`: the finding's subjects name the model function the error's key names."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import ProblemError, build, problem_finding, symbol_kit
from fransys_el.placement_ids import pin_names, symbol_ids
from fransys_el.placement_sets import DrawingScope
from fransys_el.set_findings import set_without_page_findings

from electrical_symbols import LIBRARY
from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from fransys_el.drawn_netlist import Netlist
    from fransys_el.placement_kit import SymbolKit
from fransys_model.vocab import functions, items


def test_a_kit_without_the_cards_pick_names_the_cards_function() -> None:
    d = fr.design("demo_parts")
    card = d.device("A1", None, pins=("CH01-", "CH02-"), external=True)
    lamp = d.device("P1", "DEMO-LAMP-24")
    d.series(card["CH01-"], lamp.lamp["1"], wire=(BU, 0.5))
    d.series(card["CH02-"], lamp.lamp["2"], wire=(BU, 0.5))
    model = fr.build(d).model
    card_function = next(f for f in functions(model).values() if items(model)[f.item].tag == "A1")
    kit = symbol_kit(model, LIBRARY)
    short: SymbolKit = frozendict({f: p for f, p in kit.items() if f != card_function.id})
    with pytest.raises(ProblemError) as raised:
        build(model, short, house(), LIBRARY)
    finding = problem_finding(raised.value, model)
    assert finding.code == "PLACEMENT_PROBLEM"
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (card_function.id,)


def test_an_error_with_no_key_has_no_subjects() -> None:
    model = fr.build(fr.design("demo_parts")).model
    assert problem_finding(ProblemError("anything", "fix it"), model).subjects == ()


def _set_findings(model, unit=None):
    """`set_without_page_findings` of the one set of `unit` over a model with nothing drawn."""
    kit = symbol_kit(model, LIBRARY)
    scope = DrawingScope(unit, None, frozenset(pin.sym for pin in pin_names(model, kit, symbol_ids(model, kit)).values()))
    nothing_drawn = cast("Netlist", SimpleNamespace(placed=(), net=lambda *_: ""))
    return set_without_page_findings(model, kit, nothing_drawn, [(scope, 1)])


def test_a_wired_set_with_no_page_and_no_drawn_net_is_one_set_without_page_error() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
    d.series(x1[1].inner, x2[1].inner, wire=(BU, 0.5))
    model = fr.build(d).model
    found = _set_findings(model)
    assert [f.code for f in found] == ["SET_WITHOUT_PAGE"]
    assert "no page and its nets are drawn on no other page" in found[0].message


def test_a_set_with_no_wired_port_has_no_net_so_no_set_without_page_error() -> None:
    d = fr.design("demo_parts")
    d.device("P1", "DEMO-LAMP-24")
    model = fr.build(d).model
    assert _set_findings(model) == ()


def test_a_problem_error_text_names_the_designation_not_the_id() -> None:
    d = fr.design("demo_parts")
    k1, k2 = d.device("K1", "DEMO-RLY-2CO-24"), d.device("K2", "DEMO-RLY-2CO-24")
    d.series(k1.coil["A2"], k2.coil["A1"], wire=(BU, 0.75))
    d.series(k1.coil["A1"], k2.coil["A2"], wire=(BU, 0.75))
    model = fr.build(d).model
    gone = next(f for f in functions(model).values() if items(model)[f.item].tag == "K2" and f.name == "coil")
    kit = symbol_kit(model, LIBRARY)
    short: SymbolKit = frozendict({f: p for f, p in kit.items() if f != gone.id})
    with pytest.raises(ProblemError) as raised:
        build(model, short, house(), LIBRARY)
    assert gone.id.value not in str(raised.value)
    assert "K2" in str(raised.value)
