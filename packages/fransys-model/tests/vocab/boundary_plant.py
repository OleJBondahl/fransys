"""Builders for the boundary-rating tests: a DC source in one unit, a sink in another (model-0081).

Invented data only. The source's two ports stand on the rails `+800` and `0V` of a DC supply
through their own declared nets; the sink's ports reach them through `Conductor`s.
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import make_id
from fransys_model.vocab import BoundaryValuesFacet, Rating

if TYPE_CHECKING:
    from plant import Plant

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Port, Unit
    from fransys_model.vocab.units import Boundary

RAILS = ("+800", "0V")


def source(plant: Plant, unit: Id[Unit] | None) -> tuple[Id[Port], Id[Port]]:
    """Add item `src` in `unit` whose two ports stand on `+800` and `0V`."""
    function = plant.function(plant.item("src", unit=unit), "f")
    ports = (plant.port(function, "p0"), plant.port(function, "p1"))
    for port, name in zip(ports, RAILS, strict=True):
        plant.net(f"src-{name}", (port,), potential=name)
    return ports


def state(plant: Plant, boundary: Id[Boundary], rating: Rating, *, tag: str) -> None:
    """Add the facet, keyed by `tag`, with which a unit states `rating` on `boundary`."""
    key = ("bv", tag)
    plant.add(
        BoundaryValuesFacet(
            id=make_id(BoundaryValuesFacet, key), key=key, subject=boundary, rating=rating
        )
    )
