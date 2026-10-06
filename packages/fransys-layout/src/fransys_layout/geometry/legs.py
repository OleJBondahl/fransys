"""A polyline as straight legs: repeats dropped, collinear legs joined (step 2, F2)."""

from itertools import pairwise
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

from .units import Point

type _Leg = tuple[Point, Point]


def _sign(delta: int) -> int:
    return (delta > 0) - (delta < 0)


def _joins(one: _Leg, two: _Leg, merge: Literal["same", "any"]) -> bool:
    """Whether leg `two` goes on from leg `one`: the same way along one axis, or on one line."""
    (a, b), (c, d) = one, two
    if merge == "any":
        return a.x == b.x == c.x == d.x or a.y == b.y == c.y == d.y
    second = (_sign(d.x - c.x), _sign(d.y - c.y))
    return 0 in second and (_sign(b.x - a.x), _sign(b.y - a.y)) == second


def legs[P](
    points: Iterable[P],
    *,
    at: Callable[[P], Point],
    merge: Literal["none", "same", "any"] = "same",
    ring: bool = False,
) -> tuple[tuple[P, P], ...]:
    """The legs of `points`; `"same"` joins legs going on, `"any"` a fold-back too, `ring` wraps."""
    found: list[tuple[P, P]] = []
    for first, second in pairwise(points):
        if at(first) == at(second):
            continue
        if (
            merge != "none"
            and found
            and _joins(_pair(found[-1], at), (at(first), at(second)), merge)
        ):
            found[-1] = (found[-1][0], second)
            continue
        found.append((first, second))
    if (
        ring
        and merge != "none"
        and len(found) > 1
        and _joins(_pair(found[-1], at), _pair(found[0], at), merge)
    ):
        found[0] = (found[-1][0], found[0][1])
        found.pop()
    return tuple(found)


def _pair[P](leg: tuple[P, P], at: Callable[[P], Point]) -> _Leg:
    return at(leg[0]), at(leg[1])
