"""The one text for where a stated rating comes from (EL-FACTS part A, model-0304).

A boundary rating names its unit in both rating checks; the part rating names no unit.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from boundary_plant import state
from current_plant import contactor, device, fuse, open_string
from plant import Plant
from rating_plant import load, rail, rated, supply

from fransys_model.checks.ratings import check_ratings
from fransys_model.checks.ratings_current import check_ratings_current
from fransys_model.derive.facts.stated_ratings import function_ratings, rating_source_label
from fransys_model.vocab import Rating
from fransys_model.vocab.enums import Current
from fransys_model.vocab.finding_ref import ref

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Unit


def _with_boundary(plant: Plant, item: str, rating: Rating) -> Id[Unit]:
    """Put function `f` of `item` on the boundary of a new unit, which states `rating`."""
    unit = plant.unit("board")
    boundary = plant.boundary(unit, Plant.function_id(item, "f"), key="b")
    state(plant, boundary, rating, tag="t")
    return unit


def test_the_voltage_check_names_the_unit_of_a_boundary_rating() -> None:
    plant = Plant()
    supply(plant, "a", {"A": rail("230", 0)}, name="a")
    load(plant, "d", [("A",)], rated(ac="400"))
    unit = _with_boundary(plant, "d", rated(ac="100"))
    (finding,) = check_ratings(plant.model())
    assert f"(boundary rating of {ref(unit)})" in finding.message


def test_the_current_check_names_the_unit_of_a_boundary_rating() -> None:
    plant = Plant()
    supply(plant, "dc", {"DC+": rail("985.5"), "DC-": rail("0")}, current=Current.DC)

    source = device(plant, "S", limit="150", rails=[["DC-"], ["DC+"]])
    open_string(plant, source, [fuse(plant, "F", "100"), contactor(plant, "K", "100")])
    unit = _with_boundary(plant, "K", Rating(current_dc_a=Decimal(10)))
    (finding,) = check_ratings_current(plant.model())
    assert f"(boundary rating of {ref(unit)})" in finding.message


def test_the_label_text_of_each_source() -> None:
    plant = Plant()
    supply(plant, "a", {"A": rail("230", 0)}, name="a")
    function = load(plant, "d", [("A",)], rated(ac="400"))
    unit = _with_boundary(plant, "d", rated(ac="100"))
    model = plant.model()
    labels = {rating_source_label(model, s) for s in function_ratings(model, function)}
    assert labels == {"part or template rating", f"boundary rating of {ref(unit)}"}
