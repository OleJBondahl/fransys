"""The far end of each conductor landed on a set of ports, as a list prints it (model-0205).

The one function a terminal row's ends and a connector pin's ends both read.
"""

from typing import TYPE_CHECKING

from fransys_model.vocab.tables import conductors
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Port, Unit

from .designation import end_outside_nested_unit
from .location_text import port_designation_in
from .lookups import item_of_port
from .order import natural_key

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.kernel import Model


def end_text(
    model: Model, port: Id[Port], context: Id[AspectNode] | None, unit: Id[Unit] | None
) -> str:
    """One far end as printed: `""` outside a nested `unit`, else `port_designation_in`."""
    if end_outside_nested_unit(model, item_of_port(model, port), unit):
        return ""
    return port_designation_in(model, port, context, unit=unit)


def far_ends(
    model: Model,
    near: Collection[Id[Port]],
    landed: tuple[Id[Conductor], ...],
    *,
    unit: Id[Unit] | None,
    context: Id[AspectNode] | None,
) -> tuple[tuple[Id[Conductor], ...], tuple[str, ...]]:
    """`landed` and the end each reaches from the `near` ports, by `natural_key`.

    An end is `""` when its item is outside the nested `unit`, so the tuples stay as long as
    `landed`. Conductor and end stay paired; a tie on the printed end breaks on the conductor id.
    """
    all_conductors = conductors(model)
    far = {
        c: all_conductors[c].b if all_conductors[c].a in near else all_conductors[c].a
        for c in landed
    }
    pairs = sorted(
        ((end_text(model, far[conductor], context, unit), conductor) for conductor in landed),
        key=lambda pair: (natural_key(pair[0]), pair[1]),
    )
    return tuple(c for _, c in pairs), tuple(text for text, _ in pairs)
