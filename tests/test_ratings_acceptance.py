"""RATINGS-1 step 2, acceptance 5: the rating check on demo parts, end to end (model-0079).

Every case builds a design over `examples/demo-parts`, freezes it and reads `check_ratings`. A
demo part's function template gets another rating for one test by replacing its `RatingFacet`
(`ratings_fixtures.rated`). Skipped here, already covered end to end in the model and author
packages: `SUPPLY_DIFFERS` and `POTENTIAL_IN_TWO_SUPPLIES` on hand-built records
(`test_supply_validators.py`) and the author's refusals (`test_supply.py`); only the authored-scope
route to those findings is written below.

Can-fail probes, each one Edit, run and undone: `_RAIL_LINKS` without `SWITCHED` in
`vocab/closure.py` fails the motor test; `_blocks` returning `False` fails the reversing starter
test; a pair from one port in `check_ratings` fails the changeover test; IT read as earthed in
`_rails_by_potential` fails the IT tests; deleting the demo contactor's `[function.rating]` fails
the reader test and the demo-rating case.
"""

import sys
from decimal import Decimal
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from fransys_author import Design

from fransys_model.kernel import Draft, Origin, Severity, evolve, freeze
from fransys_model.vocab import function_operating, function_rating, part_rating
from fransys_model.vocab.enums import LinkKind
from fransys_model.vocab.ratings import Operating, Rating
from fransys_model.vocab.tables import internal_links, parts
from fransys_model.vocab.validators import ALL_VALIDATORS
from fransys_model.vocab.validators.ratings import RATING_VOLTAGE_BELOW_CIRCUIT, check_ratings
from fransys_model.vocab.validators.supplies import (
    POTENTIAL_IN_TWO_SUPPLIES,
    SUPPLY_DIFFERS,
    check_supplies,
)

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ratings_fixtures import (  # noqa: E402
    RAILS,
    changeover_lamp,
    design,
    fn_id,
    freeze_design,
    lamp_on,
    line_motor,
    rated,
    rating_facet,
    reversing_starter,
    template_of,
)


def _dc_supplies(d: Design, *, earthing: str) -> None:
    """Supply `DC` (`DC+` at 800, `DC-` at 0) and the earthed supply `24V` (`+24V`)."""
    d.supply(
        "DC", current="dc", rails={"DC+": ("800", None), "DC-": ("0", None)}, earthing=earthing
    )
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})


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
        assert function_rating(model, main) == Rating(
            voltage_ac_v=Decimal(690), current_ac_a=Decimal(25)
        )
    found = check_ratings(model)
    if not fires:
        assert found == ()
        return
    (finding,) = found
    assert finding.code == RATING_VOLTAGE_BELOW_CIRCUIT
    assert finding.severity is Severity.ERROR
    assert finding.subjects == (main,)
    assert all(text in finding.message for text in ("'main'", "250", "398.4", "'L1'", "'L2'"))


# -- 2: a motor behind the contactor -------------------------------------------------------


def test_a_motor_behind_a_contactor_and_mcbs_fires_through_the_switched_links() -> None:
    model, p = line_motor()
    model = rated(model, "DEMO-MOTOR-4KW", "motor", voltage_ac_v="250")
    (finding,) = check_ratings(model)
    assert finding.subjects == (fn_id(p["m1"], "motor"),)
    assert "'motor'" in finding.message
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
def test_a_lamp_on_a_changeovers_common_and_n_stands_at_230_volts(
    volts: str, *, fires: bool
) -> None:
    """The common carries L1 and L2 as alternatives: only a rail to N stands across the lamp."""
    model, p = changeover_lamp()
    found = check_ratings(rated(model, "DEMO-LAMP-24", "lamp", voltage_ac_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(p["lamp"], "lamp"),)] if fires else [])


# -- 6, 7, 8: DC, and IT supplies ----------------------------------------------------------


@pytest.mark.parametrize(("volts", "fires"), [("600", True), ("800", False)])
def test_a_dc_device_between_plus_and_minus_400_stands_at_800_volts(
    volts: str, *, fires: bool
) -> None:
    d, _ = design()
    d.supply("DC", current="dc", rails={"+400": ("400", None), "-400": ("-400", None)})
    lamp = lamp_on(d, "+400", "-400")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_dc_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("800" in f.message and "DC" in f.message for f in found)


@pytest.mark.parametrize(
    ("potentials", "volts", "earthed_fires", "it_fires"),
    [
        (("DC-",), "600", False, True),
        (("DC+", "DC-"), "800", False, False),
        (("DC-", "+24V"), "800", False, True),
    ],
    ids=["dc-minus-alone", "dc-plus-and-minus", "dc-minus-and-earthed-24v"],
)
@pytest.mark.parametrize("earthing", ["earthed", "it"])
def test_a_dc_device_on_an_it_supply_stands_at_the_voltage_to_earth(
    potentials, volts, earthed_fires, it_fires, earthing
) -> None:
    d, _ = design()
    _dc_supplies(d, earthing=earthing)
    lamp = lamp_on(d, *potentials)
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_dc_v=volts))
    fires = it_fires if earthing == "it" else earthed_fires
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])


def test_the_message_of_an_it_pair_across_two_supplies_says_824_and_it() -> None:
    d, _ = design()
    _dc_supplies(d, earthing="it")
    lamp_on(d, "DC-", "+24V")
    (finding,) = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_dc_v="800"))
    assert "824" in finding.message
    assert "IT" in finding.message


@pytest.mark.parametrize(("earthing", "fires"), [("it", True), ("earthed", False)])
def test_an_ac_device_on_one_phase_of_an_it_supply_stands_at_398_volts(
    earthing: str, *, fires: bool
) -> None:
    d, _ = design(earthing)
    lamp = lamp_on(d, "L1")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_ac_v="250"))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("398.4" in f.message and "IT" in f.message for f in found)


# -- 9: supplies and unrated parts ---------------------------------------------------------


def _supply_codes(d: Design) -> set[str]:
    return {finding.code for finding in check_supplies(freeze_design(d))}


def test_a_model_with_supplies_and_no_rating_gives_no_finding() -> None:
    d, wire = design()
    lamp = lamp_on(d, "L1", "N")
    motor = d.item("DEMO-MOTOR-4KW", name="m1")
    d.net("L3", motor["U"], cls="power", potential="L3")
    wire(lamp["1"], motor["V"])
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


def test_two_declarations_of_one_supply_that_differ_only_in_earthing_give_supply_differs() -> None:
    d = Design(fransys_parts.load("demo_parts"))
    d.scope("a").supply("400V", current="ac", rails=RAILS)
    d.scope("b").supply("400V", current="ac", rails=RAILS, earthing="it")
    (finding,) = check_supplies(freeze_design(d))
    assert finding.code == SUPPLY_DIFFERS
    assert "earthing" in finding.message


def test_a_potential_in_two_supplies_gives_potential_in_two_supplies() -> None:
    d = Design(fransys_parts.load("demo_parts"))
    d.supply("24V", current="dc", rails={"+24V": ("24", None)})
    d.supply("PLC", current="dc", rails={"+24V": ("24", None)})
    assert _supply_codes(d) == {POTENTIAL_IN_TWO_SUPPLIES}


# -- 10: through the facade ----------------------------------------------------------------


def test_the_facade_reports_a_rating_error_and_write_raises_and_writes_nothing(tmp_path) -> None:
    library = fr.parts("demo_parts")
    template = template_of(freeze(library), "DEMO-LAMP-24", "lamp")
    weak = Draft()
    weak.add(
        rating_facet(template, voltage_ac_v="100"),
        origin=Origin(file="tests/test_ratings_acceptance.py", line=1, note=""),
    )
    d = fransys_author.Design(library)
    d.supply("400V", current="ac", rails=RAILS)
    lamp_on(d, "L1", "N")
    result = fr.build(library, d.draft(), weak)
    errors = [f for f in result.findings if f.code == RATING_VOLTAGE_BELOW_CIRCUIT]
    assert [f.severity for f in errors] == [Severity.ERROR]
    out_dir = tmp_path / "out"
    with pytest.raises(fr.BuildErrors) as raised:
        fr.write(result, out_dir)
    assert RATING_VOLTAGE_BELOW_CIRCUIT in {f.code for f in raised.value.findings}
    assert not out_dir.exists() or list(out_dir.iterdir()) == []


# -- 11: the readers on demo data ----------------------------------------------------------


def test_the_readers_give_the_demo_parts_own_rating_and_operating_values() -> None:
    d, _ = design()
    q1 = d.item("DEMO-CTR-3P-24", name="q1")
    lamp = lamp_on(d, "L1", "N")
    model = freeze_design(d)
    assert function_rating(model, fn_id(q1, "main")) == Rating(
        voltage_ac_v=Decimal(690), current_ac_a=Decimal(25)
    )
    assert function_rating(model, fn_id(q1, "coil")) is None
    cable = next(p for p in parts(model).values() if p.mpn == "DEMO-CBL-4G1.5")
    assert part_rating(model, cable.id) == Rating(voltage_ac_v=Decimal(500))
    assert function_operating(model, fn_id(lamp, "lamp")) == Operating(
        voltage_dc_v=Decimal(24), nominal_power_w=Decimal("2.4")
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
