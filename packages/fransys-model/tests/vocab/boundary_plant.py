"""Builders for the boundary-rating tests: a DC source in one unit, a sink in another (model-0081).

Invented data only. The source's two ports stand on the rails `+800` and `0V` of a DC supply
through their own declared nets; the sink's ports reach them through `Conductor`s.
"""

from typing import TYPE_CHECKING

from rating_plant import rail, supply

from fransys_model.kernel import make_id
from fransys_model.vocab import BoundaryValuesFacet, PartRatingFacet, Rating
from fransys_model.vocab.enums import Current

if TYPE_CHECKING:
    from plant import Plant

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function, Port, Unit
    from fransys_model.vocab.units import Boundary

RAILS = ("+800", "0V")


def dc_supply(plant: Plant) -> None:
    """Declare the DC supply of 800 V and 0 V, earthed."""
    supply(plant, "dc", {"+800": rail("800"), "0V": rail("0")}, current=Current.DC)


def source(plant: Plant, unit: Id[Unit] | None) -> tuple[Id[Port], Id[Port]]:
    """Add item `src` in `unit` whose two ports stand on `+800` and `0V`."""
    function = plant.function(plant.item("src", unit=unit), "f")
    ports = (plant.port(function, "p0"), plant.port(function, "p1"))
    for port, name in zip(ports, RAILS, strict=True):
        plant.net(f"src-{name}", (port,), potential=name)
    return ports


def sink(
    plant: Plant,
    unit: Id[Unit] | None,
    rails: tuple[Id[Port], Id[Port]],
    *,
    key: str = "sink",
    part_rating: Rating | None = None,
) -> Id[Function]:
    """Add item `key` in `unit` with function `in`, its two ports wired to `rails`.

    `part_rating` is the sink's part rating; `None` gives the item no part at all.
    """
    part = None
    if part_rating is not None:
        part = plant.part(key)
        facet_key = (key, "rating")
        plant.add(
            PartRatingFacet(
                id=make_id(PartRatingFacet, facet_key),
                key=facet_key,
                subject=part,
                rating=part_rating,
            )
        )
    function = plant.function(plant.item(key, unit=unit, part=part), "in")
    for index, wired in enumerate(rails):
        plant.wire(plant.port(function, f"p{index}"), wired, key=f"{key}-w{index}")
    return function


def state(plant: Plant, boundary: Id[Boundary], rating: Rating, *, tag: str) -> None:
    """Add the facet, keyed by `tag`, with which a unit states `rating` on `boundary`."""
    key = ("bv", tag)
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, key), key=key, subject=boundary, rating=rating
        )
    )
