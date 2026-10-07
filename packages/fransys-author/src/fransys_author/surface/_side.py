"""`d.layout.side` hints the edge a unit's interface stands on (HL14, author-0030)."""

from typing import TYPE_CHECKING, Any

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device
from fransys_author.surface._strip import TerminalStrip
lazy from fransys_author.handles import Terminal
lazy from fransys_author.surface._handles import Fn
lazy from fransys_model.layout import Side, SideHint
lazy from fransys_model.vocab import Boundary

from ._unused import _handles, _own

if TYPE_CHECKING:
    from fransys_author.design import Design as EngineDesign

_HANDLES = (Device, Fn, Terminal, TerminalStrip)


def _boundary_functions(engine: EngineDesign) -> set[Any]:
    """The ids of every function that is a boundary of some unit."""
    records = engine._design.draft().records()
    return {r.function for r in records if isinstance(r, Boundary)}


def _hinted(engine: EngineDesign) -> set[Any]:
    """The ids of the functions that already carry a side hint."""
    return {r.function for r in engine._design.draft().records() if isinstance(r, SideHint)}


def _interface(engine: EngineDesign, target: object) -> list[Any]:
    """The boundary functions the field `target` holds; none is a refusal."""
    handles = _handles(target, "d.layout.side", None)
    if not all(isinstance(handle, _HANDLES) for handle in handles):
        msg = "d.layout.side takes a field of a unit's interface, as `u1.bus_in`"
        raise AuthorError(msg)
    boundary = _boundary_functions(engine)
    found = [f for h in handles for f in _own(h, "d.layout.side", None) if f.id in boundary]
    if not found:
        msg = "d.layout.side: the target is no unit boundary; pass a field of the unit's interface"
        raise AuthorError(msg)
    return found


def hint_side(engine: EngineDesign, target: object, side: Side) -> None:
    """Write one `SideHint` per boundary function `target` holds; refuse a bad side or a repeat."""
    if side not in (Side.N, Side.S):
        msg = f"d.layout.side takes fr.ABOVE or fr.BELOW, not {side!r}"
        raise AuthorError(msg)
    functions = _interface(engine, target)
    again = _hinted(engine) & {f.id for f in functions}
    if again:
        msg = "d.layout.side: this interface already has a side hint; an interface takes one"
        raise AuthorError(msg)
    for function in functions:
        engine.side(function, side)
