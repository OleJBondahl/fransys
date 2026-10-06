"""Exact voltage arithmetic of the rating check (decision model-0079, model review Q4).

Every quantity is a `Fraction` built from a `Decimal`, so no comparison rounds, whatever the
digits of a rating (a `Decimal` operation rounds to the context precision, 28 digits by default).
A voltage is `exact + sqrt(s1) [+ sqrt(s2)]` (`Volt`): a DC value is exact, an AC pair voltage is
one root of a rational square, and the sum of two voltages to earth adds two of these. `exceeds`
decides `V > R` from the squares alone; only `show` takes a square root, to print V.
"""

import decimal
import itertools
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence

# 2 * cos(dphi) for dphi = 0, 60, ..., 300 degrees: integers, so the pair formula never divides.
_TWO_COS: Final = (2, 1, -1, -2, -1, 1)
_FULL_TURN: Final = 360
_STEP: Final = 60
_PRINT: Final = decimal.Context(prec=60)


@dataclass(frozen=True, slots=True)
class Volt:
    """A voltage `exact + sum(sqrt(s) for s in roots)`, with at most two roots.

    With two roots `exact` is 0: the sum of two AC voltages to earth, both IT.
    """

    exact: Fraction
    roots: tuple[Fraction, ...] = ()


@dataclass(frozen=True, slots=True)
class RailV:
    """One rail as the check sees it: its supply, kind, own values and voltage to earth.

    `max_v` and `phase` are the rail's own; `earth` is its voltage to earth: `|max_v|` in an
    earthed supply, the supply's highest voltage between two of its own rails in an IT one.
    """

    name: str
    supply: str
    it: bool
    ac: bool
    max_v: Fraction
    phase: int | None
    earth: Volt


def exact(value: Fraction) -> Volt:
    """The voltage `value` itself."""
    return Volt(value)


def root(square: Fraction) -> Volt:
    """The voltage whose square is `square`."""
    return Volt(Fraction(0), (square,))


def add(first: Volt, second: Volt) -> Volt:
    """The sum of two voltages."""
    return Volt(first.exact + second.exact, first.roots + second.roots)


def exceeds(volt: Volt, rating: Fraction) -> bool:
    """Whether `volt` is strictly above `rating`, decided on exact rational squares.

    One root `s`, exact part `e`: `e + sqrt(s) > R` is `s > (R - e)^2`, once `e > R` is ruled out.
    Two roots: `sqrt(s1) + sqrt(s2) > R` is `s1 + s2 > R^2` or else `4 s1 s2 > (R^2 - s1 - s2)^2`.
    """
    if volt.exact > rating:
        return True
    roots = volt.roots
    if not roots:
        return False
    if len(roots) == 1:
        return roots[0] > (rating - volt.exact) ** 2
    first, second = roots
    rated = rating**2
    return first + second > rated or 4 * first * second > (rated - first - second) ** 2


def _ac_square(
    first: Fraction, first_phase: int | None, second: Fraction, phase: int | None
) -> Fraction:
    """V^2 between two AC rails of their own values: Va^2 + Vb^2 - 2 Va Vb cos(dphi)."""
    step = ((first_phase or 0) - (phase or 0)) % _FULL_TURN // _STEP
    return first**2 + second**2 - _TWO_COS[step] * first * second


def common_reference(first: RailV, second: RailV) -> bool:
    """Whether two rails of one kind have a fixed relation: one supply, or two earthed DC supplies.

    Phases compare only within one supply: independent sources keep no fixed phase, so two AC
    supplies never share a reference. Two earthed DC supplies are fixed against earth; IT has none.
    """
    if first.supply == second.supply:
        return True
    return not (first.ac or second.ac or first.it or second.it)


def pair(first: RailV, second: RailV) -> Volt:
    """The voltage between two distinct rails of one kind.

    With a common reference: the AC formula on the rails' own values, or the DC difference; else
    the sum of their voltages to earth. Known limit: a transformer-fed supply's tie is unrecorded.
    """
    if not common_reference(first, second):
        return add(first.earth, second.earth)
    if first.ac:
        return root(_ac_square(first.max_v, first.phase, second.max_v, second.phase))
    return exact(abs(first.max_v - second.max_v))


def it_earth(points: Sequence[tuple[Fraction, int | None]], *, ac: bool) -> Volt | None:
    """The voltage to earth of an IT supply's rails: its highest voltage between two of them.

    `points` are the supply's `(max_v, phase)` pairs. `None` for fewer than two rails, where the
    caller uses the rail's own value.
    """
    if len(points) <= 1:
        return None
    pairs = itertools.combinations(points, 2)
    if ac:
        return root(max(_ac_square(a[0], a[1], b[0], b[1]) for a, b in pairs))
    return exact(max(abs(a[0] - b[0]) for a, b in pairs))


def magnitude(volt: Volt) -> Decimal:
    """`volt` as a `Decimal` to 60 digits, for printing and for ordering candidates only."""
    with decimal.localcontext(_PRINT):
        total = _decimal(volt.exact)
        for square in volt.roots:
            total += _decimal(square).sqrt()
        return +total


def show(volt: Volt) -> str:
    """`volt` printed to one decimal, without a trailing `.0`: 398.4, 230."""
    return f"{magnitude(volt):.1f}".removesuffix(".0")


def _decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)
