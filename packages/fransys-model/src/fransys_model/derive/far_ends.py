"""The far end of each conductor landed on a set of ports, as a list prints it (model-0205).

The one function a terminal row's ends and a connector pin's ends both read.
"""

from typing import TYPE_CHECKING

from fransys_model.vocab.tables import conductors
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Port, Unit

from .order import natural_key
from .texts.context import PrintContext
from .texts.end_text import FAR_END, end_text

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_model.kernel import Model


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
    ctx = PrintContext(reading=unit, location=context)
    all_conductors = conductors(model)
    far = {
        c: all_conductors[c].b if all_conductors[c].a in near else all_conductors[c].a
        for c in landed
    }
    pairs = sorted(
        ((end_text(model, far[conductor], FAR_END, ctx), conductor) for conductor in landed),
        key=lambda pair: (natural_key(pair[0]), pair[1]),
    )
    return tuple(c for _, c in pairs), tuple(text for text, _ in pairs)
