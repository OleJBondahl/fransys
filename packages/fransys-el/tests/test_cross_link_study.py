"""SW8 row P7.7 over the study's own instances (Rulings 40 and 43.2).

Each row is rebuilt through `fransys_el.build` from the case builder of the test that nontree.md
names, and asserts the `expected result` cell of design section 4.10. P7.1 B's box pick is
"""

from typing import TYPE_CHECKING, Any, cast

import pytest
from cross_link_cases import named, solved
from study_cases import field_case, study_model

from fransys_model.derive import function_item, function_ports, item_unit, physical_nets
from fransys_model.vocab import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Model


def _row(name: str) -> Any:
    @pytest.fixture(scope="module", name=name)
    def fixture() -> Model:
        if name == "pilot":  # the study's board with SIG realised by its wire: a declared net with no conductor is NET_UNREALISED
            return cast("Model", field_case("test_net_contact_is_not_a_spare")._built(hide=False, wired=True).model)
        return study_model(name)

    return fixture


seal, pilot, channels, units, drawn = (_row(n) for n in ("seal", "pilot", "channels", "units", "drawn"))


def _cell(model: Model) -> tuple[int, dict[str, int], dict[str, int], int, str]:
    """The measured X, R, P, reference count and a printable line, for the cell assertions."""
    layout = solved(model)
    score = layout.score
    assert score is not None
    r, p = dict(score.R), dict(score.P)
    return score.X, r, p, len(layout.references), f"X={score.X} R={r} P={p}"


def test_seal_in_has_no_crossing_and_no_reference(seal: Model) -> None:
    x, _, _, refs, shown = _cell(seal)
    named(x, 2, shown)
    assert (x, refs) == (0, 0), shown


@pytest.mark.parametrize("row", ["pilot", "drawn"])
def test_a_lamp_beside_its_coil_has_no_crossing(row: str, request: pytest.FixtureRequest) -> None:
    """The half split (BOX-SIDES) took core X from 2 to 0 on both builders."""
    x, _, p, _, shown = _cell(request.getfixturevalue(row))
    # Ruling 91 and 99.5: the lamp symbol takes attached_off_pin from 1 to 0 (main: 1)
    assert (x, p["attached_off_pin"]) == (0, 0), shown


def test_eight_coils_returned_to_channels_draw_one_net_as_a_reference_where_a_tag_stands_and_p1_zero(channels: Model) -> None:
    """The returns' own crossings are 0 (field case); the cell is every net's: 0 crossings and one reference pair.

    The wire round the tag of terminal 1 has no room (TEXT-CANDIDATES with the edge inset; WIRE_AS_REFERENCE is looks).
    """
    x, _, p, refs, shown = _cell(channels)
    assert (x, refs, p["attached_off_pin"]) == (0, 1, 0), shown


UNITS_BAR = 0  # the core measures 0 on the w02 instance (today 1, Ruling 48); the bar only falls


def _nets_across_units(model: Model) -> int:
    """Physical nets whose ports sit in more than one unit: the class that ends in stubs."""
    owner = {p: f for f in functions(model) for p in function_ports(model, f)}
    return sum(len({item_unit(model, function_item(model, owner[p])) for p in net.ports if p in owner}) > 1 for net in physical_nets(model))


def test_w02_loads_in_one_unit_have_no_cross_unit_end_and_nothing_loose(units: Model) -> None:
    """R is measured, not typed: stubs exactly when a net crosses units.

    This instance holds one unit (BLK0 and BLK1 are blocks of it), so no net crosses and R is
    empty on today's engine and the core; the stub class itself is `test_cross_links`'s two-unit
    """
    x, r, p, _, shown = _cell(units)
    expected = {"stub"} if _nets_across_units(units) else set()
    assert (x <= UNITS_BAR, set(r), p["loose"]) == (True, expected, 0), shown
