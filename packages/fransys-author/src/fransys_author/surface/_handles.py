"""Surface handles over the engine's: `Fn` and `Pin`, with every pin access checked at the line."""

from typing import Literal, overload
lazy from collections.abc import Sequence
lazy from decimal import Decimal

from fransys_author._limits import state_limits
from fransys_author.errors import AuthorAttributeError, AuthorError
from fransys_author.handles import Port
from fransys_author.surface._bar_pe import join_pe
lazy from fransys_author.design import Scope
lazy from fransys_author.handles import Fn as EngineFn
lazy from fransys_author.surface import _throws
lazy from fransys_model.derive import pin_order
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Function as ModelFunction
lazy from fransys_model.vocab import FunctionKind, Operating, Rating, SignalType

Pin = Port


def pick(
    owner: str,
    name: str,
    found: Sequence[tuple[str, Pin]],
    error: type[AuthorError] = AuthorError,
) -> Pin:
    """The one pin named `name` among `found` (function name, pin); none or two raise `error`."""
    hits = [(function, pin) for function, pin in found if pin.name == name]
    if len(hits) == 1:
        return hits[0][1]
    if hits:
        where = ", ".join(sorted(function for function, _ in hits))
        msg = f"{owner} pin {name!r} is on functions {where}; say {owner}.<function>[{name!r}]"
    else:
        names = ", ".join(sorted({pin.name for _, pin in found})) or "none"
        msg = f"{owner} has no pin {name!r}; pins: {names}"
    raise error(msg)


def fn_label(fn: Fn) -> str:
    """The text a message names a function by: `K1.coil`."""
    return f"{fn._label}.{fn._fn.name}"


class Fn:
    """One function of a device: `K1.coil`; a pin by `[ ]` (`Q1.main[2]`) or by name (`K1.coil.A1`).

    Does not accept a guessed name: an unknown pin raises and lists the pins it has.
    """

    def __init__(self, label: str, fn: EngineFn, scope: Scope | None = None) -> None:
        """Wrap the engine function `fn` of device `label`, made in `scope`; `Device` builds it."""
        self._label, self._fn, self._scope = label, fn, scope

    @property
    def id(self) -> Id[ModelFunction]:
        """The model id of the function, the key `fr.derive` reads it by after a build.

        Does not change between the draft and the built model.
        """
        return self._fn.id

    @property
    def pins(self) -> tuple[Pin, ...]:
        """The function's pins in the connector list's order: `1, 2, 10, A1`.

        Does not follow the part file's order. `a.pins[i]` is the i-th pin, counted from 0.
        """
        return tuple(sorted(self._fn.ports, key=lambda pin: pin_order(pin.name, pin.id)))

    def _pins(self) -> list[tuple[str, Pin]]:
        return [(self._fn.name, pin) for pin in self._fn.ports]

    def _screw(self, pin: Pin) -> Pin:
        """`pin`, joined to the PE net when this function is a bar: a named screw is PE too."""
        if self._fn.kind is FunctionKind.BAR:
            join_pe(self._fn, pin)
        return pin

    def __getitem__(self, marking: str | int) -> Pin:
        """The pin marked `marking`; an integer needs no quotes.

        Does not guess: an unknown marking raises and lists the pins.
        """
        return self._screw(pick(f"{self._label}.{self._fn.name}", str(marking), self._pins()))

    @overload
    def __getattr__(self, name: Literal["no", "nc"]) -> _throws.Throw: ...
    @overload
    def __getattr__(self, name: str) -> Pin: ...
    def __getattr__(self, name: str) -> Pin | _throws.Throw:
        """The pin named `name` (`K1.coil.A1`); a changeover's throw `no` or `nc`.

        Does not guess: an unknown name raises an `AttributeError` that lists the pins.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        if name in _throws.THROWS and not any(pin.name == name for pin in self._fn.ports):
            return _throws.throw(self._label, self._fn, name)
        pin = pick(f"{self._label}.{self._fn.name}", name, self._pins(), AuthorAttributeError)
        return self._screw(pin)

    def plc(self, signal: SignalType, name: str, priority: int = 0) -> Fn:
        """Core: request a PLC channel of kind `signal` (`DI`, `DO`, `AI`, `AO`) named `name`.

        Does not pick a channel: the allocation pass binds the request later.
        """
        self._fn.plc(signal.value, name, priority)
        return self

    def scale(
        self, unit: str, *, raw: tuple[int, int], eng: tuple[str | Decimal, str | Decimal]
    ) -> Fn:
        """Core: scale the raw signal range `raw` to the engineering range `eng` in `unit`.

        Does not accept a float: write the values as strings or Decimal.
        """
        self._fn.scale(unit, raw=raw, eng=eng)
        return self

    def limits(self, *, rating: Rating | None = None, operating: Operating | None = None) -> Fn:
        """Core: state the values a unit says about this boundary function.

        Example: `X1.power.limits(rating=...)`.

        Does not mark the boundary: interface=True on the device does.
        """
        state_limits(self._label, self._fn, self._scope, rating, operating)
        return self
