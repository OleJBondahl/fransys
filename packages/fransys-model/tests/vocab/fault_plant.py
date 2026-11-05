"""Builders for the prospective-fault tests: battery modules.

Invented data only. A module is a two-port `supply` function that states a DC fault current and
no current limit, so it is no position of the branch graph and the fault graph adds it (Q4).
"""

from typing import TYPE_CHECKING

from rating_plant import figures

from fransys_model.elecdef import Unit
from fransys_model.kernel import make_id
from fransys_model.vocab import Operating, OperatingFacet
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.templates import FunctionTemplate

if TYPE_CHECKING:
    from current_plant import Ports
    from plant import Plant


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
        fault_current=figures(Unit.A, None, fault),
        fault_time_constant=None if tc is None else Unit.MS(tc),
    )
    facet = OperatingFacet(id=make_id(OperatingFacet, (key,)), key=(key,), subject=template.id, operating=operating)
    plant.add(template, facet)
    function = plant.function(plant.item(key, part=part), "f", template=template.id, kind=FunctionKind.SUPPLY)
    return plant.port(function, "1"), plant.port(function, "2")
