"""`RATING_CURRENT_BELOW_BRANCH` (decision model-0088).

Every device is an item `key` with one function `f` (builders in `current_plant`); a supply and
its rails are put on the string's first port, so `port_rails` reaches the whole line. The expected
values are written by hand from the spec, never copied from the output.
"""

from typing import TYPE_CHECKING

from current_plant import (
    changeover,
    contactor,
    device,
    external,
    fuse,
    open_string,
    run,
    wire,
)
from plant import Plant
from rating_plant import rail, supply

from fransys_model.checks.ratings_current import (
    check_ratings_current,
)
from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Current
from fransys_model.vocab.finding_ref import ref

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def _dc_plant() -> Plant:
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("985.5"), "DC-": rail("0")}, current=Current.DC)
    return plant


def _source(plant: Plant, key: str = "S", limit: str = "186", *, at: int = 1) -> tuple:
    """A source limited to `limit` A DC with DC+ on its port `at` (0 or 1), DC- on the other."""
    rails = [["DC-"], ["DC-"]]
    rails[at] = ["DC+"]
    return device(plant, key, limit=limit, rails=rails)


def _ids(*keys: str) -> set:
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
    assert finding.message.endswith(
        "below its branch's 100 A DC set by the protective device of function "
        + ref(Plant.function_id("F", "f"))
    )


# -- two strings on one bus ------------------------------------------------------


# -- the reduction ---------------------------------------------------------


# -- a nested unit's boundary limit ----------------------------------------------


# -- silence -----------------------------------------------------------------------


# -- one finding per function, kind and source; order ----------------------------------------------


# -- the outside ----------------------------------------------------------------


# -- a link from a port to another function; switched links ------------------------------------


def _changeover_plant(d_amps: str, *, rated: bool = True, unrelated: bool = False) -> Plant:
    """`M` (100 A) on a changeover's make throw, `E` (120 A) on its break throw,
    the common through a 400 A full-range fuse `F` to `D`, all ends at external items.

    The changeover `CO` is rated 500 A, or with `rated` false unrated (its links are wires).
    With `unrelated` a second unrated changeover `U` has its common on `D`'s far end: in the same
    component, but nothing that `D`'s bound depends on.
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
