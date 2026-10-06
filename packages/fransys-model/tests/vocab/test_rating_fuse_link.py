"""A fuse link, an accessory of its holder, is the holder's protection rating source (model-0151).

The holder `F` is a protection function with no current of its own; each link is a function-less
child item whose part states a top-level rating. A 186 A source feeds `F`, then a contactor `K`.
"""

import re
from decimal import Decimal

from current_plant import contactor, device, fuse, open_string, rate
from plant import Plant
from rating_plant import rail, supply

from fransys_model.kernel import make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Current
from fransys_model.vocab.rating_readers import function_ratings
from fransys_model.vocab.validators.ratings_current import check_ratings_current


def _plant(k_amps: str | None, *links: tuple[str, bool]) -> Plant:
    """The string with a current-less holder `F` and one link per `(amps, partial)` in `links`."""
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("985.5"), "DC-": rail("0")}, current=Current.DC)
    line = [fuse(plant, "F", None), contactor(plant, "K", k_amps)]
    for number, (amps, partial) in enumerate(links):
        key = f"L{number}"
        part = rate(plant, key, amps, partial=partial)
        plant.item(key, part=part, parent=make_id(Item, ("F",)))
    rails = [["DC-"], ["DC+"]]
    source = device(plant, "S", limit="186", rails=rails)
    open_string(plant, source, line)
    return plant


def _bound(plant: Plant) -> str:
    """The bound, in amps, the finding on the contactor `K` names (the contactor is rated 3 A)."""
    (finding,) = [
        f
        for f in check_ratings_current(plant.model())
        if f.subjects == (Plant.function_id("K", "f"),)
    ]
    return re.search(r"branch's (\S+) A DC", finding.message).group(1)  # ty: ignore[unresolved-attribute] -- the message always holds it


def test_the_link_rating_is_a_source_of_the_holders_function() -> None:
    plant = _plant("3", ("4", False))
    sources = function_ratings(plant.model(), Plant.function_id("F", "f"))
    assert [s.rating.current_dc_a for s in sources] == [Decimal(4)]


def test_the_link_bounds_the_branch_below_the_source_limit() -> None:
    assert _bound(_plant("3", ("4", False))) == "4"


def test_several_links_bound_at_the_highest() -> None:
    assert _bound(_plant("3", ("0.5", False), ("4", False))) == "4"
    assert _bound(_plant("3", ("4", False), ("0.5", False))) == "4"


def test_a_partial_range_link_sets_no_bound() -> None:
    assert _bound(_plant("3", ("4", True))) == "186"


def test_a_full_range_link_wins_over_a_partial_range_one() -> None:
    assert _bound(_plant("3", ("400", True), ("4", False))) == "4"


def test_a_holder_with_no_link_is_unchanged() -> None:
    plant = _plant("3")
    assert function_ratings(plant.model(), Plant.function_id("F", "f")) == ()
    assert _bound(plant) == "186"


def test_a_child_with_a_function_is_not_a_link() -> None:
    plant = _plant("3")
    rated = rate(plant, "C", "4")
    plant.item("C", part=rated, parent=make_id(Item, ("F",)))
    plant.function(make_id(Item, ("C",)), "g")
    assert function_ratings(plant.model(), Plant.function_id("F", "f")) == ()


def test_a_non_protection_function_ignores_its_items_links() -> None:
    plant = _plant("3", ("4", False))
    own = function_ratings(plant.model(), Plant.function_id("K", "f"))
    assert [s.rating.current_dc_a for s in own] == [Decimal(3)]
