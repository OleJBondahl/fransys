"""The harnesses a WIRE conductor's ends sit under (model-0171).

A wire's end port belongs to the nearest harness among its item and that item's ancestors;
`checks` and `derive` read this one fact.
"""

from fransys_model.derive.facts.roles import conductor_role
from fransys_model.derive.facts.units import is_harness, item_chain
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import conductors, functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Item, Port


def port_harness(model: Model, port: Id[Port]) -> Id[Item] | None:
    """The nearest harness at or above the item that owns `port`, or `None`."""
    item = functions(model)[ports(model)[port].function].item
    return next((node for node in item_chain(model, item) if is_harness(model, node)), None)


def wire_harnesses(model: Model, conductor: Id[Conductor]) -> tuple[Id[Item], ...]:
    """The distinct harnesses of a WIRE conductor's ends, sorted; empty for any other kind."""
    if not conductor_role(model, conductor).wire:
        return ()
    record = conductors(model)[conductor]
    found = {port_harness(model, end) for end in (record.a, record.b)}
    return tuple(sorted(harness for harness in found if harness is not None))


@digest_cached(DIGEST_CACHE_SIZE)
def harnesses_with_wires(model: Model) -> frozenset[Id[Item]]:
    """Every harness that has a single wire: all its wires' ends agree on it."""
    found = (wire_harnesses(model, conductor) for conductor in conductors(model))
    return frozenset(harness for (harness,) in (h for h in found if len(h) == 1))
