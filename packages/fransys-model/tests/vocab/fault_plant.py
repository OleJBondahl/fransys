"""Builders for the prospective-fault tests: battery modules, a three-pole breaker, unit moves.

Invented data only. A module is a two-port `supply` function that states a DC fault current and
no current limit, so it is no position of the branch graph and the fault graph adds it (Q4).
"""

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

from current_plant import rate

from fransys_model.kernel import make_id
from fransys_model.vocab import Operating, OperatingFacet
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import FunctionKind, LinkKind, PortRole
from fransys_model.vocab.templates import FunctionTemplate, PortTemplate

if TYPE_CHECKING:
    from collections.abc import Collection

    from current_plant import Ports
    from plant import Plant

    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Unit


def module(plant: Plant, key: str, fault: str | None = "6000", tc: str | None = "2") -> Ports:
    """Item `key`: a battery module, ports `1` (minus) and `2` (plus), `fault` A at `tc` ms."""
    part = plant.part(key)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "f")),
        key=(key, "f"),
        part=part,
        name="f",
        kind=FunctionKind.SUPPLY,
    )
    operating = Operating(
        fault_current_dc_a=None if fault is None else Decimal(fault),
        fault_time_constant_ms=None if tc is None else Decimal(tc),
    )
    facet = OperatingFacet(
        id=make_id(OperatingFacet, (key,)), key=(key,), subject=template.id, operating=operating
    )
    plant.add(template, facet)
    function = plant.function(
        plant.item(key, part=part), "f", template=template.id, kind=FunctionKind.SUPPLY
    )
    return plant.port(function, "1"), plant.port(function, "2")


def breaker(plant: Plant, key: str, amps_ac: str = "16") -> list[Ports]:
    """Item `key`: one `protection` function, three poles: (`1`, `2`), (`3`, `4`), (`5`, `6`)."""
    part = rate(plant, key, None, amps_ac=amps_ac)
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, (key, "f")),
        key=(key, "f"),
        part=part,
        name="f",
        kind=FunctionKind.PROTECTION,
    )
    pins = [
        PortTemplate(
            id=make_id(PortTemplate, (key, "f", str(n))),
            key=(key, "f", str(n)),
            function=template.id,
            name=str(n),
            role=PortRole.GENERIC,
        )
        for n in range(1, 7)
    ]
    plant.add(template, *pins)
    for at in (0, 2, 4):
        plant.link(pins[at], pins[at + 1], LinkKind.CONDUCTIVE, key=f"link-{key}-{at}")
    function = plant.function(
        plant.item(key, part=part), "f", template=template.id, kind=FunctionKind.PROTECTION
    )
    ports = [plant.port(function, pin.name, template=pin.id) for pin in pins]
    return [(ports[at], ports[at + 1]) for at in (0, 2, 4)]


def into(plant: Plant, unit: Id[Unit], keys: Collection[str]) -> None:
    """Put the items keyed `keys` into `unit`."""
    plant.records[:] = [
        dataclasses.replace(record, unit=unit)
        if isinstance(record, Item) and record.key[0] in keys
        else record
        for record in plant.records
    ]
