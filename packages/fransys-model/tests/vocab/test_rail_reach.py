"""`rail_reach`: the supplies a function reaches and the voltage across it (RATINGS-3 R8, R11)."""

from plant import Plant
from rating_plant import AC_400, load, rail, rated, supply

from fransys_model.vocab import voltage
from fransys_model.vocab.enums import Current
from fransys_model.vocab.rail_reach import (
    Stand,
    ports_by_function,
    rails_by_potential,
    reach_of,
    reached_supplies,
    voltage_across,
    worst_stand,
)

HV = {"HV+": rail("400"), "HV-": rail("-400")}


def test_a_function_on_one_dc_supply_reaches_that_supply_only() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    supply(plant, "hv", HV, current=Current.DC)
    function = load(plant, "d", [("HV+",), ("HV-",)], rated(dc="800"))
    load(plant, "other", [("L1",), ("N",)], rated(ac="250"))  # another function's supply
    assert reached_supplies(plant.model())[function] == {"hv"}


def test_a_function_across_two_supplies_reaches_both() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    supply(plant, "hv", HV, current=Current.DC)
    function = load(plant, "d", [("L1",), ("HV+",)], rated(ac="250"))
    assert reached_supplies(plant.model())[function] == {"ac", "hv"}


def test_a_function_on_no_rail_reaches_no_supply() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    function = load(plant, "d", [("X",)], rated(ac="250"))
    assert reached_supplies(plant.model())[function] == set()


def test_the_voltage_across_l1_and_l2_is_the_400_v_stand() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    function = load(plant, "d", [("L1",), ("L2",)], rated(ac="250"))
    model = plant.model()
    reach = reach_of(model, function, rails_by_potential(model), ports_by_function(model))
    stand = voltage_across(reach, ac=True)
    assert stand is not None
    assert [r.name for r in stand.rails] == ["L1", "L2"]
    assert voltage.show(stand.volt) == "398.4"
    assert voltage_across(reach, ac=False) is None


def test_the_worst_stand_wins_over_a_smaller_pair_at_the_same_function() -> None:
    plant = Plant()
    supply(plant, "ac", AC_400)
    function = load(plant, "d", [("L1",), ("N",), ("L2",)], rated(ac="250"))
    model = plant.model()
    reach = reach_of(model, function, rails_by_potential(model), ports_by_function(model))
    stand = voltage_across(reach, ac=True)
    assert stand is not None
    assert [r.name for r in stand.rails] == ["L1", "L2"]  # 398 V beats L1-N at 230 V


def test_of_equal_stands_the_first_by_rail_names_is_the_worst() -> None:
    """`worst_stand`, the one rule both the voltage check and the breaking check read."""
    plant = Plant()
    supply(plant, "ac", AC_400)
    lookup = rails_by_potential(plant.model())
    to_earth = [Stand(lookup[name].earth, (lookup[name],)) for name in ("L3", "L1", "L2")]
    assert [r.name for r in worst_stand(to_earth).rails] == ["L1"]
    pair = Stand(voltage.pair(lookup["L1"], lookup["L3"]), (lookup["L1"], lookup["L3"]))
    assert worst_stand([*to_earth, pair]) is pair
