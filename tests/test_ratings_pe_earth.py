"""PE-EARTH: a rail carried by a PE-class net is earth, 0 V to earth in every supply (model-0085).

Demo parts only. A supply that lists `PE` as a rail (the spec's old Q2 example did) must not give
it the earth-fault voltage of an IT supply: a function that reaches only PE stands at 0 V, and a
pair with PE stands at the other rail's voltage to earth.

Can-fail probes, each one Edit, run and undone: `_earth_potentials` filtering on `and False` in
`vocab/validators/ratings.py` fails the only-PE test, the cross-supply test (both IT cases), the
listed-value test and the IT DC test; keeping the earth rails among the `live` points of an IT
supply fails the IT DC test alone.
"""

import sys
from pathlib import Path

import fransys_parts
import pytest
from fransys_author import Design

from fransys_model.vocab.validators.ratings import check_ratings

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    # `--import-mode=importlib` (root pyproject.toml) never puts this folder on `sys.path`.
    sys.path.insert(0, str(_TESTS_DIR))

from ratings_fixtures import RAILS, fn_id, freeze_design, rated  # noqa: E402

_WITH_PE = {**RAILS, "PE": ("0", None)}
_IT_RAILS = {"IL1": ("230", 0), "IL2": ("230", 120), "PE": ("0", None)}


def _lamp(d: Design, name: str, *potentials: str):
    """A demo lamp whose port 1, then port 2, is on a net of that potential (`PE` in class `pe`)."""
    lamp = d.item("DEMO-LAMP-24", name=name)
    for port, potential in zip(("1", "2"), potentials, strict=False):
        cls = "pe" if potential == "PE" else "power"
        d.net(f"{name}.{port}", lamp[port], cls=cls, potential=potential)
    return lamp


def _design() -> Design:
    return Design(fransys_parts.load("demo_parts"))


@pytest.mark.parametrize("earthing", ["earthed", "it"])
def test_a_function_reaching_only_pe_stands_at_zero_volts_in_any_supply(earthing: str) -> None:
    d = _design()
    d.supply("400V", current="ac", rails=_WITH_PE, earthing=earthing)
    on_pe = _lamp(d, "h1", "PE")
    on_l1 = _lamp(d, "h2", "L1")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_ac_v="250"))
    assert fn_id(on_pe, "lamp") not in {s for f in found for s in f.subjects}
    # the same plant with the IT supply live: L1 alone stands at 398.4 V to earth, so it fires
    assert [f.subjects for f in found] == ([(fn_id(on_l1, "lamp"),)] if earthing == "it" else [])


@pytest.mark.parametrize("earthing", ["earthed", "it"])
@pytest.mark.parametrize(("volts", "fires"), [("250", False), ("229", True)])
def test_a_function_between_l1_and_pe_of_one_supply_stands_at_230_volts(
    earthing: str, volts: str, *, fires: bool
) -> None:
    d = _design()
    d.supply("400V", current="ac", rails=_WITH_PE, earthing=earthing)
    lamp = _lamp(d, "h1", "L1", "PE")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_ac_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("230" in f.message and "398" not in f.message for f in found)


@pytest.mark.parametrize("earthing", ["earthed", "it"])
@pytest.mark.parametrize(("volts", "fires"), [("250", False), ("229", True)])
def test_pe_of_an_it_supply_across_a_rail_of_another_supply_stands_at_that_rails_230_volts(
    earthing: str, volts: str, *, fires: bool
) -> None:
    """The supply that lists PE is IT or earthed: the pair is the same, PE being earth."""
    d = _design()
    d.supply("400V", current="ac", rails=RAILS)
    d.supply("PEHOLDER", current="ac", rails=_IT_RAILS, earthing=earthing)
    lamp = _lamp(d, "h1", "L1", "PE")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_ac_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("230" in f.message and "628" not in f.message for f in found)


def test_a_pe_rail_is_at_zero_volts_whatever_value_a_supply_lists_for_it() -> None:
    d = _design()
    d.supply("24V", current="dc", rails={"+24V": ("24", None), "PE": ("5", None)})
    lamp = _lamp(d, "h1", "+24V", "PE")
    (finding,) = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_dc_v="20"))
    assert finding.subjects == (fn_id(lamp, "lamp"),)
    assert "24 V" in finding.message  # 24 - 0, not 24 - 5


@pytest.mark.parametrize(("volts", "fires"), [("30", False), ("20", True)])
def test_pe_is_no_point_of_an_it_supplys_own_voltage(volts: str, *, fires: bool) -> None:
    """Rails +24V and +48V of an IT DC supply stand 24 V apart; a listed PE at 0 V is not a third
    point, or +24V would stand at 48 V to earth."""
    d = _design()
    d.supply(
        "DCX",
        current="dc",
        rails={"+24V": ("24", None), "+48V": ("48", None), "PE": ("0", None)},
        earthing="it",
    )
    lamp = _lamp(d, "h1", "+24V")
    _lamp(d, "h2", "PE")  # a PE-class net carries the PE rail: only then is it earth
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_dc_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("24 V to earth" in f.message for f in found)
