"""Which poles of a function are in series: one wired N pin and one wired S pin (design 2.1).

The caller maps each pin's symbol facing onto `sides`; a port missing from it is sideless.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.pole_lists import poles_of
from fransys_model.derive.rows_series_pairs import SeriesPair
from fransys_model.layout import Side
from fransys_model.vocab.closure import net_of
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Function, Port

__all__ = ["series_pairs"]


def series_pairs(
    model: Model, function: Id[Function], sides: Mapping[Id[Port], Side]
) -> tuple[SeriesPair, ...]:
    """Each pole of `function` with one wired N pin and one wired S pin, in pole order."""
    found: list[SeriesPair] = []
    for index, pins in enumerate(_poles(model, function)):
        north = _lone_wired(model, pins, sides, Side.N)
        south = _lone_wired(model, pins, sides, Side.S)
        if north is not None and south is not None:
            found.append(SeriesPair(pole=index, north=north, south=south))
    return tuple(found)


def _poles(model: Model, function: Id[Function]) -> tuple[tuple[Id[Port], ...], ...]:
    """The function's ports by pole, in pole order; a function with no poles is one pole."""
    mine = [p for p in ports(model).values() if p.function == function]
    own = {p.template: p.id for p in mine if p.template is not None}
    found = poles_of(model, functions(model)[function].kind, own)
    if not found:
        return (tuple(p.id for p in mine),)
    return tuple((own[pole.ends[0].id], own[pole.ends[1].id]) for pole in found)


def _lone_wired(
    model: Model, pins: tuple[Id[Port], ...], sides: Mapping[Id[Port], Side], side: Side
) -> Id[Port] | None:
    """The one wired pin of `pins` facing `side`, or `None` when there is not exactly one."""
    wired = [p for p in pins if sides.get(p) is side and _is_wired(model, p)]
    return wired[0] if len(wired) == 1 else None


def _is_wired(model: Model, port: Id[Port]) -> bool:
    """A port is wired when its physical net holds another port."""
    net = net_of(model, port)
    return net is not None and len(net.ports) > 1
