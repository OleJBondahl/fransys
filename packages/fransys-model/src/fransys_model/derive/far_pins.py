"""The far port of each conductor at a set of ports (model-0340, the home of `stub_far`'s reach).

One fact for a stub's far end and for the layout's page-free `far_ends`: the `ConductorEnd`s
over every conductor and the `MateEnd`s over every mate pair at any `near` port, in `order.stub_far_order` order.
A harness wire's conductor is a pair like any other (R546).
"""

lazy from collections.abc import Iterable

from fransys_model.derive.facts.conductor_facts import conductor_ends, drawn_conductors
from fransys_model.derive.facts.mates import mate_pairs
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.order import stub_far_order
from fransys_model.derive.rows_drawn import ConductorEnd, MateEnd
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Port

__all__ = ["far_pins"]


def reach(model: Model, near: Iterable[Id[Port]]) -> list[ConductorEnd | MateEnd]:
    """Every conductor end and mate end at any `near` port, lowest far port first."""
    by_port = build_indexes(model).conductors_by_port
    drawn = drawn_conductors(model)
    pairs = mate_pairs(model)
    found: list[ConductorEnd | MateEnd] = []
    for port in near:
        for conductor in filter(drawn.__contains__, by_port.get(port, ())):
            a, b = conductor_ends(model, conductor)
            found.append(ConductorEnd(conductor=conductor, port=port, far=b if a == port else a))
        found += (MateEnd(mate=m, port=port, far=b if a == port else a) for m, a, b in pairs if port in (a, b))
    return stub_far_order(model, found)


def far_pins(model: Model, near: Iterable[Id[Port]]) -> tuple[tuple[Id[Port], Id[Port]], ...]:
    """`(near, far)` for each conductor or mate pair at a `near` port; the far end is `conductor_ends`'.

    Ordered by `order.stub_far_order`: a conductor before a mate, the far port's printed designation, then the near port's, then the key.
    A bridge is no wire and gives no pair; a port no conductor reaches gives no pair; a conductor between two `near` ports gives two.
    `stub_far` reads `reach`.
    """
    return tuple((end.port, end.far) for end in reach(model, near))
