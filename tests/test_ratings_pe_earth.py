"""PE-EARTH: a rail carried by a PE-class net is earth, 0 V to earth in every supply (model-0085).

Demo parts only. A supply that lists `PE` as a rail (the spec's old Q2 example did) must not give
it the earth-fault voltage of an IT supply: a function that reaches only PE stands at 0 V, and a
"""

import fransys_parts
import pytest
from fransys_author.design import Design
from ratings_fixtures import RAILS, fn_id, freeze_design, rated

from fransys_model.checks.ratings import check_ratings

_WITH_PE = {**RAILS, "PE": ("0", None)}
_PE_RAILS = {"IL1": ("230", 0), "IL2": ("230", 120), "PE": ("0", None)}


def _lamp(d: Design, name: str, *potentials: str):
    """A demo lamp whose port 1, then port 2, is on a net of that potential (`PE` in class `pe`)."""
    lamp = d.item("DEMO-LAMP-24", name=name)
    for port, potential in zip(("1", "2"), potentials, strict=False):
        cls = "pe" if potential == "PE" else "power"
        d.net(f"{name}.{port}", lamp[port], cls=cls, potential=potential)
    return lamp


def _design() -> Design:
    return Design(fransys_parts.load("demo_parts"))


def test_a_function_reaching_only_pe_stands_at_zero_volts_in_a_supply() -> None:
    d = _design()
    d.supply("400V", current="ac", rails=_WITH_PE)
    on_pe = _lamp(d, "h1", "PE")
    _lamp(d, "h2", "L1")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_ac_v="250"))
    assert fn_id(on_pe, "lamp") not in {s for f in found for s in f.subjects}
    assert [f.subjects for f in found] == []


@pytest.mark.parametrize(("volts", "fires"), [("250", False), ("229", True)])
def test_a_function_between_l1_and_pe_of_one_supply_stands_at_230_volts(volts: str, *, fires: bool) -> None:
    d = _design()
    d.supply("400V", current="ac", rails=_WITH_PE)
    lamp = _lamp(d, "h1", "L1", "PE")
    found = check_ratings(rated(freeze_design(d), "DEMO-LAMP-24", "lamp", voltage_ac_v=volts))
    assert [f.subjects for f in found] == ([(fn_id(lamp, "lamp"),)] if fires else [])
    assert all("230" in f.message and "398" not in f.message for f in found)


@pytest.mark.parametrize(("volts", "fires"), [("250", False), ("229", True)])
def test_pe_of_a_supply_across_a_rail_of_another_supply_stands_at_that_rails_230_volts(volts: str, *, fires: bool) -> None:
    """The supply that lists PE is earthed: PE is earth, so the pair stands at the rail's 230 V."""
    d = _design()
    d.supply("400V", current="ac", rails=RAILS)
    d.supply("PEHOLDER", current="ac", rails=_PE_RAILS)
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
