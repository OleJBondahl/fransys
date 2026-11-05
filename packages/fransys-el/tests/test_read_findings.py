"""`read_findings` (R267): connection to undrawn."""
# NET_POTENTIAL_CONFLICT 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.
# NET_SHORTED 1 per default-salt build set (KI-461): planted_model or demo_model 24 V to 0 V short through strip and mate.

from fransys_el import Skipped, read_findings
from fransys_el.placement_skips import FUNCTION_WITHOUT_SYMBOL
from placement_fixtures import planted_model
lazy import fransys as fr

from fransys_model.kernel import Model, Severity, render_id
from fransys_model.vocab import conductors, ports


def _codes(model: Model, code: str) -> list[fr.Finding]:
    return [f for f in read_findings(model, ()) if f.code == code]


def test_a_conductor_with_a_skipped_end_is_one_warning_naming_that_end() -> None:
    model = planted_model()
    conductor = next(iter(conductors(model).values()))
    function = ports(model)[conductor.a].function
    skipped = [Skipped("function", render_id(function), FUNCTION_WITHOUT_SYMBOL)]
    found = [f for f in read_findings(model, skipped) if f.code == "CONNECTION_TO_UNDRAWN"]
    assert found
    assert all(f.severity is Severity.WARNING and f.fix for f in found)
    assert any(conductor.a in f.subjects for f in found)
    assert _codes(model, "CONNECTION_TO_UNDRAWN") == []
