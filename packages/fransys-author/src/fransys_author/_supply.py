"""A `SupplySystem` from `s.supply(...)`; phase rules run here first.

A DC rail has no phase and an AC `max_v` is not negative: authoring's own checks.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from fransys_model.derive import rail_phase_problem
from fransys_model.elecdef import Current
from fransys_model.kernel import make_id
from fransys_model.vocab import Rail, SupplySystem

from ._decimal import as_decimal
from ._keys import scoped
from ._origin import caller_origin
from .errors import AuthorError

if TYPE_CHECKING:
    from .design import Scope
    from .handles import Port

_RAIL_FIELDS = 2  # a rail is (max_v, phase)


def supply_rails(name: str, kind: Current, rails: Mapping[str, tuple[str | Decimal, int | None]]) -> frozendict[str, Rail]:
    """The supply's checked rails, refusing what authoring can see wrong."""
    if not isinstance(rails, Mapping):
        msg = f"supply {name!r} rails must be a mapping of potential to (max_v, phase), not {rails!r}"
        raise AuthorError(msg)
    if not rails:
        msg = f"supply {name!r} declares no rails; give at least one potential"
        raise AuthorError(msg)
    for potential in rails:
        if not isinstance(potential, str):
            msg = f"supply {name!r} rail potential must be a str, not {potential!r}"
            raise AuthorError(msg)
    return frozendict({potential: _rail(name, potential, spec, kind) for potential, spec in rails.items()})


def _rail(supply: str, potential: str, spec: object, kind: Current) -> Rail:
    where = f"supply {supply!r} rail {potential!r}"
    if not isinstance(spec, tuple) or len(spec) != _RAIL_FIELDS:
        msg = f"{where} must be a (max_v, phase) pair, not {spec!r}"
        raise AuthorError(msg)
    raw_v, phase = spec
    max_v = _max_v(where, raw_v)
    _check_phase(where, kind, max_v, phase)
    rail = Rail(max_v=max_v, phase=phase)
    problem = rail_phase_problem(kind, rail)
    if problem is not None:
        msg = f"{where} {problem}"
        raise AuthorError(msg)
    return rail


def _check_phase(where: str, kind: Current, max_v: Decimal, phase: object) -> None:
    """Refuse a phase that is not an int or None, a DC phase, or an AC negative max_v."""
    if phase is not None and (isinstance(phase, bool) or not isinstance(phase, int)):
        msg = f"{where} phase must be an int or None, not {phase!r}"
        raise AuthorError(msg)
    if kind is Current.DC:
        if phase is not None:
            msg = f"{where} is DC and cannot have a phase ({phase})"
            raise AuthorError(msg)
    elif max_v < 0:
        msg = f"{where} is AC and max_v is an RMS value, so it cannot be negative ({max_v})"
        raise AuthorError(msg)


def _max_v(where: str, raw: str | Decimal) -> Decimal:
    if isinstance(raw, bool):
        msg = f"{where} max_v must be a str or Decimal, not a bool ({raw!r})"
        raise AuthorError(msg)
    try:
        max_v = as_decimal(raw, field=f"{where} max_v")
    except InvalidOperation:
        msg = f"{where} max_v {raw!r} is not a number"
        raise AuthorError(msg) from None
    if not max_v.is_finite():
        msg = f"{where} max_v must be finite, not {raw!r}"
        raise AuthorError(msg)
    return max_v


class SupplyScope:
    """The `supply` method of `Scope`, kept here because `design.py` has no room to grow."""

    __slots__ = ()

    def supply(
        self: Scope,
        name: str,
        *,
        current: str,
        rails: Mapping[str, tuple[str | Decimal, int | None]],
        pins: Sequence[Port] = (),
    ) -> None:
        """Declare a supply system and its rails.

        `rails` maps potential to `(max_v, phase)`; `pins` are the ports they stand on.
        Raises `AuthorError` on a bad value, or on `name` declared twice here with other content.
        """
        key = scoped(self._prefix, "supply", name)
        if current not in ("ac", "dc"):
            msg = f"{current!r} is not a valid current; valid: ac, dc"
            raise AuthorError(msg)
        kind = Current[current.upper()]
        checked = supply_rails(name, kind, rails)
        record = SupplySystem(
            id=make_id(SupplySystem, key),
            key=key,
            name=name,
            current=kind,
            rails=checked,
            unit=self._unit,
            pins=tuple(sorted({pin.id for pin in pins})),
        )
        self._design._add(record, caller_origin())
