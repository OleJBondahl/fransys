"""`problem_finding`: the finding's subjects name the model function the error's key names."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import ProblemError, build, problem_finding, symbol_kit

from electrical_symbols import LIBRARY
from fransys_model.kernel import Severity

if TYPE_CHECKING:
    from fransys_el.placement_kit import SymbolKit
from fransys_model.vocab import functions, items


def test_a_kit_without_the_cards_pick_names_the_cards_function() -> None:
    d = fr.design("demo_parts")
    card = d.device("A1", None, pins=("CH01-", "CH02-"), external=True)
    lamp = d.device("P1", "DEMO-LAMP-24")
    d.detail.wire(card["CH01-"], lamp.lamp["1"], wire=(BU, 0.5))
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
