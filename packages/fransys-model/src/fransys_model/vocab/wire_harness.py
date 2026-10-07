"""The harnesses a WIRE conductor's ends sit under (HA2, model-0171).

Lives in `vocab` so `validators` and `derive.wire_harness` read one fact; a wire's end port
belongs to the nearest harness among its item and that item's ancestors.
"""

from typing import TYPE_CHECKING

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, digest_cached

from .enums import ConductorKind
from .membership import is_harness, item_chain
from .tables import conductors, functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model

    from .connectivity import Conductor
    from .core import Item, Port


def port_harness(model: Model, port: Id[Port]) -> Id[Item] | None:
    """The nearest harness at or above the item that owns `port`, or `None`."""
    item = functions(model)[ports(model)[port].function].item
    return next((node for node in item_chain(model, item) if is_harness(model, node)), None)


def wire_harnesses(model: Model, conductor: Id[Conductor]) -> tuple[Id[Item], ...]:
    """The distinct harnesses of a WIRE conductor's ends, sorted; empty for any other kind."""
    record = conductors(model)[conductor]
    if record.kind is not ConductorKind.WIRE:
        return ()
    found = {port_harness(model, end) for end in (record.a, record.b)}
    return tuple(sorted(harness for harness in found if harness is not None))


@digest_cached(DIGEST_CACHE_SIZE)
def harnesses_with_wires(model: Model) -> frozenset[Id[Item]]:
    """Every harness that has a single wire: all its wires' ends agree on it."""
    found = (wire_harnesses(model, conductor) for conductor in conductors(model))
    return frozenset(harness for (harness,) in (h for h in found if len(h) == 1))
