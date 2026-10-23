"""SPARE-TERMINALS (R356): a terminal none of whose nets has a second end is listed, not drawn."""

import pytest
from conventions_fixtures import house
from fransys_el import build, skipped_findings, symbol_kit
from fransys_el.placement_skips import SPARE_TERMINAL
from placement_fixtures import planted_model, sid

from electrical_symbols import LIBRARY
from fransys_model.kernel import Severity


@pytest.mark.rule("SPARE-TERMINALS")
def test_a_spare_terminal_is_no_symbol_and_one_info_finding_names_the_spares() -> None:
    """The planted strips hold wired terminals and spares: spares leave the problem, one INFO."""
    model = planted_model()
    problem, skipped = build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    drawn = {s.id for s in problem.symbols}
    spares = {sid(model, t) for t in ("2.terminal", "3.terminal")}
    assert not spares & drawn
    assert {sid(model, t) for t in ("1.terminal", "U1-1.terminal")} <= drawn
    assert len([s for s in skipped if s.reason == SPARE_TERMINAL]) >= 1
    found = [f for f in skipped_findings(model, skipped) if f.code == "SPARE_TERMINALS"]
    assert len(found) == 1
    assert found[0].severity is Severity.INFO
    assert str(len(found[0].subjects)) in found[0].message


@pytest.mark.rule("SPARE-TERMINALS")
def test_an_unwired_contact_of_a_wired_relay_is_a_spare_function_with_one_info() -> None:
    """The w02 relays have an unwired contact function each: left off, one INFO, no loose symbol."""
    from study_cases import study_model

    model = study_model("units")
    problem, skipped = build(model, symbol_kit(model, LIBRARY), house(), LIBRARY)
    on_a_net = {r.sym for n in problem.nets for r in n.pins}
    assert on_a_net >= {s.id for s in problem.symbols}
    found = [f for f in skipped_findings(model, skipped) if f.code == "SPARE_FUNCTIONS"]
    assert len(found) == 1
    assert found[0].severity is Severity.INFO
    assert len(found[0].subjects) == 6
