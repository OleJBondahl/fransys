"""Builders for the rating-voltage tests: rails, supplies and one function standing on rails.

Invented data only. A port stands on a rail through its own declared `Net` with that potential,
so `port_rails` reads it without a conductor.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_model.kernel import make_id
from fransys_model.vocab import PartRatingFacet, Rating
from fransys_model.vocab.enums import Current, Earthing
from fransys_model.vocab.supply_system import Rail, SupplySystem

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from plant import Plant

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Function, Port, Unit


def rail(max_v: str, phase: int | None = None) -> Rail:
    """A rail of `max_v` volts at `phase` degrees."""
    return Rail(max_v=Decimal(max_v), phase=phase)


# Three phases of 230 V at 0, 120 and 240 degrees and a neutral at 0 V.
AC_400 = {"L1": rail("230", 0), "L2": rail("230", 120), "L3": rail("230", 240), "N": rail("0")}


def rated(ac: str | None = None, dc: str | None = None) -> Rating:
    """A rating with `voltage_ac_v` and `voltage_dc_v` from strings."""
    return Rating(
        voltage_ac_v=None if ac is None else Decimal(ac),
        voltage_dc_v=None if dc is None else Decimal(dc),
    )


def supply(  # noqa: PLR0913 -- one keyword per thing a test varies
    plant: Plant,
    key: str,
    rails: Mapping[str, Rail],
    *,
    name: str | None = None,
    current: Current = Current.AC,
    earthing: Earthing = Earthing.EARTHED,
    unit: Id[Unit] | None = None,
    pins: Sequence[Id[Port]] = (),
    fault_current_a: Decimal | None = None,
) -> Id[SupplySystem]:
    """Add a supply; `name` defaults to the key; `unit`, `pins` and the fault are its own."""
    record = SupplySystem(
        id=make_id(SupplySystem, (key,)),
        key=(key,),
        name=key if name is None else name,
        current=current,
        earthing=earthing,
        rails=frozendict(rails),
        fault_current_a=fault_current_a,
        unit=unit,
        pins=tuple(sorted(pins)),
    )
    plant.add(record)
    return record.id


def load(
    plant: Plant, key: str, ports_on: Sequence[Sequence[str]], rating: Rating | None
) -> Id[Function]:
    """Add item `key` with one function `f` whose ports stand on the rails `ports_on` names.

    `rating` is the part's rating; `None` adds no rating facet at all.
    """
    part = plant.part(key)
    if rating is not None:
        facet = PartRatingFacet(
            id=make_id(PartRatingFacet, (key,)), key=(key,), subject=part, rating=rating
        )
        plant.add(facet)
    function = plant.function(plant.item(key, part=part), "f")
    for index, rails in enumerate(ports_on):
        port = plant.port(function, f"p{index}")
        for name in rails:
            plant.net(f"{key}-{index}-{name}", (port,), potential=name)
    return function
