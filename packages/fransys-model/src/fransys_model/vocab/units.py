"""Vocabulary: a unit's interface (units spec U3)."""

from fransys_model.kernel import AuthoringKey, Id, Value, record

from .core import Function, Unit


@record(kind="boundary")
class Boundary:
    """A function that is part of a unit's interface.

    Example: `u.boundary(x1)` in `io_board` makes connector `X1` the board's
    interface. One function may be the boundary of several units, for a board
    connector that is also its cabinet's external connector.
    """

    id: Id[Boundary]
    key: AuthoringKey
    unit: Id[Unit]
    function: Id[Function]
    ext: frozendict[str, Value] = frozendict()


@record(kind="unused_boundary")
class UnusedBoundary:
    """An integrator's declaration that a boundary function is left unconnected on purpose.

    Example: a cabinet's spare field terminal, declared via `unused=` on `d.add`.
    """

    id: Id[UnusedBoundary]
    key: AuthoringKey
    function: Id[Function]
    ext: frozendict[str, Value] = frozendict()
