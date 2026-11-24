"""`RATING_CURRENT_BELOW_BRANCH` (decision model-0088).

Every device is an item `key` with one function `f` (builders in `current_plant`); a supply and
its rails are put on the string's first port, so `port_rails` reaches the whole line. The expected
"""

import dataclasses
from typing import TYPE_CHECKING

from current_plant import (
    Ports,
    changeover,
    contactor,
    device,
    external,
    fuse,
    hub,
    open_string,
    run,
    wire,
)
from fault_plant import module
from plant import Plant
from rating_plant import rail, supply

from fransys_model.checks.ratings_current import (
    check_ratings_current,
)
from fransys_model.derive.facts.fault.prospective import oversized_chains
from fransys_model.elecdef import Current
from fransys_model.kernel import Origin, evolve, make_id
from fransys_model.layout import layout_of
from fransys_model.layout.house_ratings import RatingsForm
from fransys_model.vocab.core import Item
from fransys_model.vocab.finding_ref import ref

if TYPE_CHECKING:
    from fransys_model.kernel import Finding, Id, Model
    from fransys_model.vocab.core import Function


def _dc_plant() -> Plant:
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("985.5"), "DC-": rail("0")}, current=Current.DC)
    return plant


def _source(plant: Plant, key: str = "S", limit: str = "186", *, at: int = 1) -> Ports:
    """A source limited to `limit` A DC with DC+ on its port `at` (0 or 1), DC- on the other."""
    rails = [["DC-"], ["DC-"]]
    rails[at] = ["DC+"]
    return device(plant, key, limit=limit, rails=rails)


def _ids(*keys: str) -> set[Id[Function]]:
    return {Plant.function_id(key, "f") for key in keys}


def _the_finding(plant: Plant) -> Finding:
    (finding,) = check_ratings_current(plant.model())
    return finding


# -- The partial-range fuse bounds nothing --------------------------------------


# -- A full-range fuse bounds the branch ---------------------------------------


def _fused(device_amps: str) -> Plant:
    """A 150 A source, a full-range 100 A fuse, a device rated `device_amps`."""
    plant = _dc_plant()
    line = [fuse(plant, "F", "100"), contactor(plant, "K", device_amps)]
    open_string(plant, _source(plant, limit="150"), line)
    return plant


def test_a_full_range_fuse_bounds_the_branch_at_its_own_rating() -> None:
    assert check_ratings_current(_fused("120").model()) == ()
    finding = _the_finding(_fused("90"))
    assert finding.subjects == (Plant.function_id("K", "f"),)
    assert finding.message.endswith("below its branch's 100 A DC set by the protective device of function " + ref(Plant.function_id("F", "f")))


# -- two strings on one bus ------------------------------------------------------


# -- the reduction ---------------------------------------------------------


# -- a nested unit's boundary limit ----------------------------------------------


# -- silence -----------------------------------------------------------------------


# -- one finding per function, kind and source; order ----------------------------------------------


# -- the outside ----------------------------------------------------------------


# -- a link from a port to another function; switched links ------------------------------------


def _changeover_plant(d_amps: str, *, rated: bool = True, unrelated: bool = False, extra: int = 0) -> Plant:
    """`M` (100 A) on a changeover's make throw, `E` (120 A) on its break throw,
    the common through a 400 A full-range fuse `F` to `D`, all ends at external items.

    The changeover `CO` is rated 500 A, or with `rated` false unrated (its links are wires).
    """
    plant = _dc_plant()
    common, make, brk = changeover(plant, "CO", "500" if rated else None)
    for tag, throw in (("M", make), ("E", brk)):
        source = _source(plant, tag, "100" if tag == "M" else "120")
        wire(plant, source[0], external(plant, f"T{tag}"))
        wire(plant, source[1], throw)
    line = [fuse(plant, "F", "400"), device(plant, "D", amps=d_amps)]
    end = external(plant, "Td")
    run(plant, common, line, end)
    if unrelated:
        wire(plant, changeover(plant, "U", None)[0], end)
    for index in range(extra):
        wire(plant, changeover(plant, f"U{index}")[0], end)
    return plant


_D_110 = (
    f"function {ref(Plant.function_id('D', 'f'))} is rated 110 A DC (part or template rating), "
    "below its branch's 120 A DC set by the source of function "
    f"{ref(Plant.function_id('E', 'f'))}, "
    f"with item {ref(make_id(Item, ('CO',)))} at rest"
)


def test_the_message_names_only_the_item_that_matters() -> None:
    """`U` is in `D`'s component and is enumerated, but `D`'s 120 A holds whatever it does."""
    assert _the_finding(_changeover_plant("110", unrelated=True)).message == _D_110


# -- every item is enumerated ------------------------------------------------------


def test_nine_items_are_all_enumerated() -> None:
    """`CO` and nine more share one component: no cap, so `D`'s bound is still the one finding."""
    assert [f.code for f in check_ratings_current(_changeover_plant("110", extra=9).model())] == ["RATING_CURRENT_BELOW_BRANCH"]


# -- the state budget ----------------------------------------------------------------


def _with_budget(plant: Plant, max_solves: int) -> Model:
    """The plant's model with the `[ratings] max_solves` record set to `max_solves`."""
    model = plant.model()
    (old,) = layout_of(model, RatingsForm).values()
    return evolve(model, remove=[old.id], put=[dataclasses.replace(old, max_solves=max_solves)], origin=Origin(file="test", line=0, note="budget"))


def test_a_block_over_the_budget_is_an_error_naming_its_items() -> None:
    """One both-throw item (`CO`) is 2 solves: a budget of 1 names it, a budget of 2 names none."""
    plant = _changeover_plant("110")
    (over,) = [f for f in check_ratings_current(_with_budget(plant, 1)) if f.code == "RATING_STATES_OVER_BUDGET"]
    assert over.subjects == (make_id(Item, ("CO",)),)
    assert [f.code for f in check_ratings_current(_with_budget(plant, 2))] == ["RATING_CURRENT_BELOW_BRANCH"]


def test_a_fault_chain_over_the_budget_is_an_error_naming_its_items() -> None:
    """A 6000 A module feeds fuse `G` through the changeover `CO`: a budget of 1 names `CO`'s chain, the default budget names none."""
    plant = Plant()
    plus, minus, node = hub(plant, "P"), hub(plant, "M"), hub(plant, "N")
    plant.net("bus+", (plus,), potential="B+")
    plant.net("bus-", (minus,), potential="B-")
    supply(plant, "bat", {"B+": rail("48"), "B-": rail("0")}, current=Current.DC, pins=(plus, minus))
    run(plant, minus, [module(plant, "m", "6000", "2")], plus)
    common, make, _ = changeover(plant, "CO")
    wire(plant, plus, common)
    wire(plant, make, node)
    run(plant, node, [fuse(plant, "G", "10")], minus)
    model = _with_budget(plant, 1)
    assert oversized_chains(plant.model()) == ()
    assert oversized_chains(model) == ((make_id(Item, ("CO",)),),)
    assert [f.subjects for f in check_ratings_current(model) if f.code == "RATING_STATES_OVER_BUDGET"] == [(make_id(Item, ("CO",)),)]
