"""The rating check on demo parts, end to end (model-0079).

Every case builds a design over `examples/demo-parts`, freezes it and reads `check_ratings`. A
demo part's function template gets another rating for one test by replacing its `RatingFacet`
"""

import fransys as fr
import fransys_parts
import pytest
from _expected_codes import expect_codes
from fransys_author.design import Design
from ratings_fixtures import (
    RAILS,
    changeover_lamp,
    design,
    fn_id,
    freeze_design,
    lamp_on,
    line_motor,
    rated,
    rating_facet,
    rating_of,
    reversing_starter,
    rng,
    template_of,
)
from root_library import freeze

from fransys_model.checks import ALL_VALIDATORS
from fransys_model.checks.ratings import (
    RATING_CURRENT_KIND_UNSTATED,
    RATING_VOLTAGE_BELOW_CIRCUIT,
    check_ratings,
)
from fransys_model.checks.supplies import (
    POTENTIAL_IN_TWO_SUPPLIES,
    SUPPLY_DIFFERS,
    check_supplies,
)
from fransys_model.derive import function_operating, function_rating, part_rating
from fransys_model.elecdef import Current, LinkKind, Unit
from fransys_model.kernel import Draft, Origin, Severity, evolve
from fransys_model.vocab import Operating
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import internal_links, parts

# -- 1: a three-pole contactor -------------------------------------------------------------


@pytest.mark.parametrize(
    ("volts", "fires"),
    [("250", True), ("400", False), (None, False)],
    ids=["250", "400", "demo-690"],
)
def test_a_three_pole_contactor_on_l1_l2_l3_fires_below_398_4_volts(volts, fires) -> None:
    model, p = line_motor()
    main = fn_id(p["q1"], "main")
    if volts is not None:
        model = rated(model, "DEMO-CTR-3P-24", "main", voltage_ac_v=volts)
    else:  # the demo part's own rating is what passes: an unrated contactor would pass too
        assert function_rating(model, main) == rating_of(voltage_ac_v=690, current_ac_a=25)
    found = check_ratings(model)
    if not fires:
        assert found == ()
        return
    (finding,) = found
    assert finding.code == RATING_VOLTAGE_BELOW_CIRCUIT
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (main,)
    assert ref(main) in finding.message
    assert all(text in finding.message for text in ("250", "398.4", "'L1'", "'L2'"))


# -- 2: a motor behind the contactor -------------------------------------------------------


def test_a_motor_behind_a_contactor_and_mcbs_fires_through_the_switched_links() -> None:
    model, p = line_motor()
    model = rated(model, "DEMO-MOTOR-4KW", "motor", voltage_ac_v="250")
    (finding,) = check_ratings(model)
    assert finding.subjects == (fn_id(p["m1"], "motor"),)
    assert ref(fn_id(p["m1"], "motor")) in finding.message
    assert "250" in finding.message
    assert "398.4" in finding.message


def test_without_the_switched_links_the_motor_is_unchecked() -> None:
    model, _ = line_motor()
    model = rated(model, "DEMO-MOTOR-4KW", "motor", voltage_ac_v="250")
    switched = [i for i, link in internal_links(model).items() if link.kind is LinkKind.SWITCHED]
    assert switched
    assert check_ratings(evolve(model, remove=switched)) == ()


# -- 3, 4, 5: a lamp beside the other loads ------------------------------------------------


@pytest.mark.parametrize(("volts", "fires"), [("250", False), ("230", False), ("229", True)])
def test_a_lamp_on_l1_and_n_stands_at_230_volts(volts: str, *, fires: bool) -> None:
    d, _ = design()
    lamp = lamp_on(d, "L1", "N")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_ac_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("230" in f.message and "'L1'" in f.message for f in found)


def test_a_reversing_starter_leaves_the_lamps_on_l1_alone_and_fires_only_the_motor() -> None:
    """Both lamps (`h1` on L1 and N, `h2` across two L1 ports) rated 250 V pass: the starter
    carries L3 to the L1 net's ports only if a rail may enter another declared net."""
    model, p = reversing_starter()
    model = rated(model, "DEMO-LAMP-24", "lamp", voltage_ac_v="250")
    assert check_ratings(model) == ()
    model = rated(model, "DEMO-MOTOR-4KW", "motor", voltage_ac_v="250")
    (finding,) = check_ratings(model)
    assert finding.subjects == (fn_id(p["m1"], "motor"),)
    assert "398.4" in finding.message


@pytest.mark.parametrize(("volts", "fires"), [("250", False), ("229", True)])
def test_a_lamp_on_a_changeovers_common_and_n_stands_at_230_volts(volts: str, *, fires: bool) -> None:
    """The common carries L1 and L2 as alternatives: only a rail to N stands across the lamp."""
    model, p = changeover_lamp()
    found = check_ratings(rated(model, "DEMO-LAMP-24", "lamp", voltage_ac_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(p["lamp"], "lamp"),)] if fires else [])


# -- 6, 7, 8: DC supplies ---------------------------------------------------------------


@pytest.mark.parametrize(("volts", "fires"), [("600", True), ("800", False)])
def test_a_dc_device_between_plus_and_minus_400_stands_at_800_volts(volts: str, *, fires: bool) -> None:
    d, _ = design()
    d.supply("DC", current="dc", rails={"+400": ("400", None), "-400": ("-400", None)})
    lamp = lamp_on(d, "+400", "-400")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_dc_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("800" in f.message and "DC" in f.message for f in found)


def test_the_demo_lamp_states_24_volts_and_gives_the_error_on_a_230_volt_path() -> None:
    """C6.6a (parts-0022): the shipped lamp rating is what fires, with no `rated(...)` override."""
    d, _ = design()
    lamp = lamp_on(d, "L1", "N")
    (finding,) = check_ratings(freeze_design(d))
    assert finding.code == RATING_VOLTAGE_BELOW_CIRCUIT
    assert finding.subjects == (fn_id(lamp, "lamp"),)
    assert "24 V AC" in finding.message


def _heater_on(*potentials: str, **rating: str):
    """The unrated demo heater, rated `rating`, whose `+` then `-` is on the given potentials."""
    d, _ = design()
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})
    heater = d.item("DEMO-HEATER-24", name="h1")
    for port, potential in zip(("+", "-"), potentials, strict=False):
        d.net(potential, heater[port], cls="power", potential=potential)
    model = freeze_design(d)
    return rated(model, "DEMO-HEATER-24", "load", **rating), fn_id(heater, "load")


def test_a_dc_only_rating_on_ac_rails_gives_the_kind_warning() -> None:
    """C6.6b (model-0231): a DC rating alone is silent to the voltage check, and now warned."""
    model, load = _heater_on("L1", "N", voltage_dc_v="24")
    (finding,) = check_ratings(model)
    assert finding.code == RATING_CURRENT_KIND_UNSTATED
    assert finding.severity is Severity.WARNING
    assert finding.subjects == (load,)
    assert finding.message == (
        f"{ref(load)} states a DC rating only (part or template rating) and stands on AC rails "
        'L1, N at 230 V: state voltage = [{ nom = "<n> V", at = ["AC"] }] in its [rating], or use a part rated for AC'
    )


def test_an_ac_only_rating_on_a_dc_rail_gives_the_kind_warning() -> None:
    model, load = _heater_on("+24V", voltage_ac_v="250")
    (finding,) = check_ratings(model)
    assert (finding.code, finding.subjects) == (RATING_CURRENT_KIND_UNSTATED, (load,))
    assert "AC rating only" in finding.message
    assert "DC rail +24V at 24 V" in finding.message


@pytest.mark.parametrize(
    ("potentials", "rating"),
    [
        (("+24V",), {"voltage_dc_v": "24"}),
        (("L1", "N"), {"voltage_ac_v": "250"}),
        (("L1", "N"), {"voltage_ac_v": "250", "voltage_dc_v": "250"}),
        (("L1", "N"), {"current_dc_a": "2"}),
    ],
    ids=["dc-on-dc", "ac-on-ac", "both-kinds", "no-voltage"],
)
def test_a_rating_that_fits_its_rails_or_states_no_voltage_gives_no_kind_warning(potentials, rating) -> None:
    model, _ = _heater_on(*potentials, **rating)
    assert [f for f in check_ratings(model) if f.code == RATING_CURRENT_KIND_UNSTATED] == []


# -- 9: supplies and unrated parts ---------------------------------------------------------


def _supply_codes(d: Design) -> set[str]:
    return {finding.code for finding in check_supplies(freeze_design(d))}


def test_a_model_with_supplies_and_no_rating_gives_no_finding() -> None:
    d, wire = design()
    other = d.item("DEMO-MOTOR-4KW", name="m2")  # an unrated part on mains (the lamp is rated 24 V)
    motor = d.item("DEMO-MOTOR-4KW", name="m1")
    d.net("L1", other["U"], cls="power", potential="L1")
    d.net("N", other["V"], cls="power", potential="N")
    d.net("L3", motor["U"], cls="power", potential="L3")
    wire(other["W"], motor["V"])
    model = freeze_design(d)
    assert check_ratings(model) == ()
    assert [f for validator in ALL_VALIDATORS for f in validator(model) if "RATING" in f.code] == []


def test_two_scopes_declaring_supply_24v_with_equal_content_give_no_finding() -> None:
    d = Design(fransys_parts.load("demo_parts"))
    for name in ("a", "b"):
        d.scope(name).supply("24V", current="dc", rails={"+24V": ("24", None)})
    assert _supply_codes(d) == set()


def test_two_scopes_declaring_supply_24v_with_different_content_give_supply_differs() -> None:
    d = Design(fransys_parts.load("demo_parts"))
    d.scope("a").supply("24V", current="dc", rails={"+24V": ("24", None)})
    d.scope("b").supply("24V", current="dc", rails={"+24V": ("28", None)})
    assert _supply_codes(d) == {SUPPLY_DIFFERS}


def test_a_potential_in_two_supplies_gives_potential_in_two_supplies() -> None:
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})
    d.supply("PLC", current="dc", rails={"+24V": ("24", None)})
    assert _supply_codes(d) == {POTENTIAL_IN_TWO_SUPPLIES}


# -- 10: through the facade ----------------------------------------------------------------


def test_the_facade_reports_a_rating_error_and_write_raises_and_writes_nothing(tmp_path) -> None:
    library = fr.parts("demo_parts")
    template = template_of(freeze(library), "DEMO-HEATER-24", "load")  # states no rating
    weak = Draft()
    weak.add(
        rating_facet(template, voltage_ac_v="100"),
        origin=Origin(file="tests/test_ratings_acceptance.py", line=1, note=""),
    )
    d = Design(library)
    d.supply("400V", current="ac", rails=RAILS)
    heater = d.item("DEMO-HEATER-24", name="h1")
    for port, potential in (("+", "L1"), ("-", "N")):
        d.net(potential, heater[port], cls="power", potential=potential)
    result = fr.build(library, d.draft(), weak)
    expect_codes(result, RATING_VOLTAGE_BELOW_CIRCUIT)
    errors = [f for f in result.findings if f.code == RATING_VOLTAGE_BELOW_CIRCUIT]
    assert [f.severity for f in errors] == [Severity.ERROR]
    out_dir = tmp_path / "out"
    with pytest.raises(fr.BuildFailedError) as raised:
        fr.write(result, out_dir)
    assert RATING_VOLTAGE_BELOW_CIRCUIT in {f.code for f in raised.value.findings}
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


# -- 11: the readers on demo data ----------------------------------------------------------


def test_the_readers_give_the_demo_parts_own_rating_and_operating_values() -> None:
    d, _ = design()
    q1 = d.item("DEMO-CTR-3P-24", name="q1")
    lamp = lamp_on(d, "L1", "N")
    model = freeze_design(d)
    assert function_rating(model, fn_id(q1, "main")) == rating_of(voltage_ac_v=690, current_ac_a=25)
    assert function_rating(model, fn_id(q1, "coil")) is None
    cable = next(p for p in parts(model).values() if p.mpn == "DEMO-CBL-4G1.5")
    assert part_rating(model, cable.id) == rating_of(voltage_ac_v=500)
    assert function_operating(model, fn_id(lamp, "lamp")) == Operating(
        voltage=(rng(Unit.V, current=Current.DC, nom=24),), nominal_power=Unit.W("2.4")
    )


# -- determinism ---------------------------------------------------------------------------


def test_the_findings_do_not_depend_on_the_order_of_the_declarations() -> None:
    def findings(*, reverse: bool):
        model, _ = reversing_starter(reverse=reverse)
        model = rated(model, "DEMO-MOTOR-4KW", "motor", voltage_ac_v="250")
        model = rated(model, "DEMO-LAMP-24", "lamp", voltage_ac_v="229")
        return check_ratings(model)

    forward = findings(reverse=False)
    assert len(forward) == 3  # the motor, the lamp h1 (230 V) and the bridge lamp h2 (230 V)
    assert findings(reverse=True) == forward
