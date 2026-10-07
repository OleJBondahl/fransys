"""Which edge of a middle outline each interface takes, and their order along it (HL13, HL14)."""

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_model.kernel import Id

HALF = Fraction(1, 2)
TOP, BOTTOM = True, False  # an edge: the outline's top or its bottom


@dataclass(frozen=True)
class InterfaceEdge:
    """One interface of a middle outline: HL13's facts; the engine fills `flow` and `width`."""

    function: Id[Any]
    designation: str
    order: tuple[object, ...]
    hint: bool | None
    line: bool
    share: Fraction
    flow: bool | None = None
    width: Fraction = Fraction(0)


def _given(item: InterfaceEdge) -> bool | None:
    """The edge HL13 steps 1 and 2 fix, or `None` for a line interface with no hint."""
    if item.hint is not None:
        return item.hint
    return None if item.line else (BOTTOM if item.flow is None else item.flow)


def _fits(old: Fraction, new: Fraction, share: Fraction) -> bool:
    """Whether a move leaves the edges at least as even; on an exact tie only with share >= 1/2."""
    return new < old or (new == old and share >= HALF)


def _moves(
    interfaces: Sequence[InterfaceEdge],
) -> tuple[dict[Id[Any], bool], list[tuple[Id[Any], Fraction, Fraction]]]:
    """The split and its trail: each tried move's (function, top, bottom), the refused one last."""
    given = {i.function: edge for i in interfaces if (edge := _given(i)) is not None}
    top = sum((i.width for i in interfaces if given.get(i.function) is TOP), Fraction(0))
    bottom = sum((i.width for i in interfaces if given.get(i.function) is not TOP), Fraction(0))
    result = dict(given)
    trail: list[tuple[Id[Any], Fraction, Fraction]] = []
    rest = [i for i in interfaces if i.function not in given]
    for item in sorted(rest, key=lambda i: (-i.share, i.order)):
        new_top, new_bottom = top + item.width, bottom - item.width
        trail.append((item.function, new_top, new_bottom))
        if not _fits(abs(top - bottom), abs(new_top - new_bottom), item.share):
            break
        top, bottom = new_top, new_bottom
        result[item.function] = TOP
    return result, trail


def edges(interfaces: Sequence[InterfaceEdge]) -> dict[Id[Any], bool]:
    """HL13: each interface's edge: its hint, else its column's flow, else the even split.

    The split ranks line interfaces by supply share, starts them below and moves each to the top
    while the edges stay as even. The first that does not fit stops it; the rest stay below.
    """
    split, _ = _moves(interfaces)
    return {i.function: split.get(i.function, BOTTOM) for i in interfaces}


def along(functions: Sequence[Id[Any]], reach_x: Mapping[Id[Any], int]) -> tuple[Id[Any], ...]:
    """The interfaces of one edge in the x order of the columns their lines reach, ties as given."""
    return tuple(sorted(functions, key=lambda f: reach_x[f]))
