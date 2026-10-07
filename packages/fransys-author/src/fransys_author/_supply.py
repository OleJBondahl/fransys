"""A `SupplySystem` from `s.supply(...)` (spec model-review Q2); phase rules run here first.

A DC rail has no phase and an AC `max_v` is not negative: authoring's own checks.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Protocol

from fransys_model.kernel import make_id
from fransys_model.vocab import Current, Earthing, Rail, SupplySystem, rail_phase_problem

from ._decimal import as_decimal
from ._enums import member
from ._keys import scoped
from ._origin import caller_origin
from .errors import AuthorError

if TYPE_CHECKING:
    from fransys_model.kernel import AuthoringKey, Id, Origin, Record
    from fransys_model.vocab import Port as ModelPort
    from fransys_model.vocab import Unit

    from .handles import Port

_RAIL_FIELDS = 2  # a rail is (max_v, phase)


def build_supply_system(  # noqa: PLR0913, PLR0917 -- the supply's own fields, the fault values (R3), its unit and pins (R6)
    key: AuthoringKey,
    name: str,
    current: str,
    rails: Mapping[str, tuple[str | Decimal, int | None]],
    earthing: str,
    fault: tuple[str | int | Decimal | None, str | int | Decimal | None] = (None, None),
    unit: Id[Unit] | None = None,
    pins: Sequence[Id[ModelPort]] = (),
) -> SupplySystem:
    """The `SupplySystem` `s.supply(name, ...)` writes, refusing what authoring can see wrong."""
    kind = member(Current, current, field="current")
    earth = member(Earthing, earthing, field="earthing")
    if not isinstance(rails, Mapping):
        msg = (
            f"supply {name!r} rails must be a mapping of potential to (max_v, phase), not {rails!r}"
        )
        raise AuthorError(msg)
    if not rails:
        msg = f"supply {name!r} declares no rails; give at least one potential"
        raise AuthorError(msg)
    for potential in rails:
        if not isinstance(potential, str):
            msg = f"supply {name!r} rail potential must be a str, not {potential!r}"
            raise AuthorError(msg)
    built = {potential: _rail(name, potential, spec, kind) for potential, spec in rails.items()}
    return SupplySystem(
        id=make_id(SupplySystem, key),
        key=key,
        name=name,
        current=kind,
        earthing=earth,
        rails=frozendict(built),
        fault_current_a=_positive(f"supply {name!r} fault_current_a", fault[0]),
        fault_time_constant_ms=_positive(f"supply {name!r} fault_time_constant_ms", fault[1]),
        unit=unit,
        pins=tuple(sorted(set(pins))),
    )


def _positive(where: str, raw: str | int | Decimal | None) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        msg = f"{where} must be a positive number, not a bool ({raw!r})"
        raise AuthorError(msg)
    try:
        value = as_decimal(str(raw) if isinstance(raw, int) else raw, field=where)
    except InvalidOperation:
        msg = f"{where} {raw!r} is not a number"
        raise AuthorError(msg) from None
    if not value.is_finite() or value <= 0:
        msg = f"{where} must be a positive number, not {raw!r}"
        raise AuthorError(msg)
    return value


def _rail(supply: str, potential: str, spec: object, kind: Current) -> Rail:
    where = f"supply {supply!r} rail {potential!r}"
    if not isinstance(spec, tuple) or len(spec) != _RAIL_FIELDS:
        msg = f"{where} must be a (max_v, phase) pair, not {spec!r}"
        raise AuthorError(msg)
    raw_v, phase = spec
    max_v = _max_v(where, raw_v)
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
    rail = Rail(max_v=max_v, phase=phase)
    problem = rail_phase_problem(kind, rail)
    if problem is not None:
        msg = f"{where} {problem}"
        raise AuthorError(msg)
    return rail


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


class _Declaring(Protocol):
    """What `SupplyScope.supply` reads of its `Scope`."""

    @property
    def _prefix(self) -> AuthoringKey: ...

    @property
    def _unit(self) -> Id[Unit] | None: ...

    @property
    def _design(self) -> _Recorder: ...


class _Recorder(Protocol):
    """What the scope needs back from the `Design` that made it."""

    def _add(self, record: Record, origin: Origin) -> None: ...


class SupplyScope:
    """The `supply` method of `Scope`, kept here because `design.py` has no room to grow."""

    __slots__ = ()

    def supply(  # noqa: PLR0913 -- the supply's own fields, the fault values (R3) and its pins (R6)
        self: _Declaring,
        name: str,
        *,
        current: str,
        rails: Mapping[str, tuple[str | Decimal, int | None]],
        earthing: str = "earthed",
        fault_current_a: str | int | Decimal | None = None,
        fault_time_constant_ms: str | int | Decimal | None = None,
        pins: Sequence[Port] = (),
    ) -> None:
        """Declare a supply system and its rails (spec model-review Q2).

        `rails` maps potential to `(max_v, phase)`; `pins` are the ports they stand on (R6).
        Raises `AuthorError` on a bad value, or on `name` declared twice here with other content.
        """
        key = scoped(self._prefix, "supply", name)
        fault = (fault_current_a, fault_time_constant_ms)
        record = build_supply_system(
            key, name, current, rails, earthing, fault, self._unit, [pin.id for pin in pins]
        )
        self._design._add(record, caller_origin())
