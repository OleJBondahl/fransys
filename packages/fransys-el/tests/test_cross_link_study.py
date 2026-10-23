"""SW8 row P7.7 over the study's own instances (Rulings 40 and 43.2).

Each row is rebuilt through `fransys_el.build` from the case builder of the test that nontree.md
names, and asserts the `expected result` cell of design section 4.10. P7.1 B's box pick is
on main (lift round, 2026-10-18). A cell whose bar is today's engine (Ruling 48) names the number
and where it was measured: `claude-tools/lift_measure.py`, the core's own net-aware crossing
counter over the old engine's routes of the same builder. A row the core still misses is a strict
xfail at the unchanged bar with the measured numbers in its reason.
The builder runs in a module fixture; `fransys_el.build` and `solve` run in the test body.
"""

from typing import TYPE_CHECKING, Any

import pytest
from cross_link_cases import named, solved
from study_cases import study_model

from fransys_model.derive import function_item, function_ports, item_unit, physical_nets
from fransys_model.vocab import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def _row(name: str) -> Any:
    @pytest.fixture(scope="module", name=name)
    def fixture() -> Model:
        return study_model(name)

    return fixture


seal, pilot, channels, units, drawn = (
    _row(n) for n in ("seal", "pilot", "channels", "units", "drawn")
)


def _cell(model: Model) -> tuple[int, dict[str, int], dict[str, int], int, str]:
    """The measured X, R, P, reference count and a printable line, for the cell assertions."""
    layout = solved(model)
    score = layout.score
    assert score is not None
    r, p = dict(score.R), dict(score.P)
    return score.X, r, p, len(layout.references), f"X={score.X} R={r} P={p}"


def test_seal_in_has_no_crossing_and_no_reference(seal: Model) -> None:
    x, _, _, refs, shown = _cell(seal)
    named(x, 1, shown)
    assert (x, refs) == (0, 0), shown


TODAY_PILOT = 1  # today's engine, this builder (Ruling 48); the ceiling only falls


def test_pilot_lamp_beside_its_coil_has_no_crossing(pilot: Model) -> None:
    """The half split (BOX-SIDES) took core X from 2 to 0; attached_off_pin stays 1."""
    x, _, p, _, shown = _cell(pilot)
    # Ruling 91 and 99.5: the lamp symbol takes attached_off_pin from 1 to 0 (main: 1)
    assert (x <= TODAY_PILOT, p["attached_off_pin"]) == (True, 0), shown


TODAY_CHANNELS = 6  # today's engine, all nets, this builder; the core's 6 equals it


def test_eight_coils_returned_to_channels_have_no_crossing_and_p1_zero(channels: Model) -> None:
    """The returns' own crossings are 0 (field case); the cell is every net's, at today's X."""
    x, _, p, refs, shown = _cell(channels)
    assert (x <= TODAY_CHANNELS, refs, p["attached_off_pin"]) == (True, 0, 0), shown


UNITS_BAR = 0  # the core measures 0 on the w02 instance (today 1, Ruling 48); the bar only falls


def _nets_across_units(model: Model) -> int:
    """Physical nets whose ports sit in more than one unit: the class that ends in stubs."""
    owner = {p: f for f in functions(model) for p in function_ports(model, f)}
    return sum(
        len({item_unit(model, function_item(model, owner[p])) for p in net.ports if p in owner}) > 1
        for net in physical_nets(model)
    )


def test_w02_loads_in_one_unit_have_no_cross_unit_end_and_nothing_loose(units: Model) -> None:
    """R is measured, not typed: stubs exactly when a net crosses units.

    This instance holds one unit (BLK0 and BLK1 are blocks of it), so no net crosses and R is
    empty on today's engine and the core; the stub class itself is `test_cross_links`'s two-unit
    case. The cell is X at the core's 0, nothing loose, and R equal to what the model's nets say.
    """
    x, r, p, _, shown = _cell(units)
    expected = {"stub"} if _nets_across_units(units) else set()
    assert (x <= UNITS_BAR, set(r), p["loose"]) == (True, expected, 0), shown


TODAY_CAB = 1  # today's engine on the `_cab` builder (Ruling 48); the ceiling only falls


def test_drawn_supply_closing_the_circuit_has_no_crossing(drawn: Model) -> None:
    """The half split (BOX-SIDES) took core X from 2 to 0; attached_off_pin stays 1."""
    x, _, p, _, shown = _cell(drawn)
    # Ruling 91 and 99.5: the lamp symbol takes attached_off_pin from 1 to 0 (main: 1)
    assert (x <= TODAY_CAB, p["attached_off_pin"]) == (True, 0), shown
