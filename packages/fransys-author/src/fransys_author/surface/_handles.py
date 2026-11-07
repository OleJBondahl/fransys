"""Surface handles over the engine's: `Fn` and `Pin`, with every pin access checked at the line."""

from typing import Literal, overload
lazy from collections.abc import Sequence
lazy from decimal import Decimal

from fransys_author.errors import AuthorAttributeError, AuthorError
from fransys_author.handles import Port
lazy from fransys_author.design import Scope
lazy from fransys_author.handles import Fn as EngineFn
lazy from fransys_author.surface import _fn_pole, _throws
lazy from fransys_author.surface._removed import refuse
lazy from fransys_model.derive import pin_order
lazy from fransys_model.kernel import Id, natural_join
lazy from fransys_model.vocab import Function as ModelFunction
lazy from fransys_model.vocab import SignalType, identifier

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
        where = natural_join(function for function, _ in hits)
        msg = f"{owner} pin {name!r} is on functions {where}; say {owner}.<function>[{name!r}]"
    else:
        names = natural_join({pin.name for _, pin in found}) or "none"
        msg = f"{owner} has no pin {name!r}; pins: {names}"
    raise error(msg)


def attribute_pin(name: str, found: Sequence[tuple[str, Pin]]) -> str:
    """The pin name that attribute `name` stands for: `P_1_L1` for the pin `1/L1`.

    Does not guess: a name that matches no pin, or several, stays as written for `pick` to report.
    """
    if any(pin.name == name for _, pin in found):
        return name
    named = {pin.name for _, pin in found if identifier(pin.name) == name}
    return named.pop() if len(named) == 1 else name


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

    def __getitem__(self, marking: str | int) -> Pin:
        """The pin marked `marking`; an integer needs no quotes.

        Does not guess: an unknown marking raises and lists the pins.
        """
        return pick(f"{self._label}.{self._fn.name}", str(marking), self._pins())

    @overload
    def __getattr__(self, name: Literal["no", "nc"]) -> _throws.Throw: ...
    @overload
    def __getattr__(self, name: str) -> Pin: ...
    def __getattr__(self, name: str) -> Pin | _throws.Throw:
        """The pin named `name` (`K1.coil.A1`); a changeover's throw `no` or `nc`.

        Does not guess: an unknown name raises an `AttributeError` that lists the pins.
        """
        if name.startswith("__") or "_fn" not in vars(self):  # copy, unpickle: no recursion
            raise AuthorAttributeError(name)
        if name == "limits":
            refuse("Fn", name)
        if name in _throws.THROWS and not any(pin.name == name for pin in self._fn.ports):
            return _throws.throw(self._label, self._fn, name)
        owner, pins = f"{self._label}.{self._fn.name}", self._pins()
        return pick(owner, attribute_pin(name, pins), pins, AuthorAttributeError)

    def pole(self, n: int, /) -> _fn_pole.FnPole:
        """Core: one pole of this function as a series element, counted from 1 in pole order.

        Example: `d.series(s1.main.pole(2), f2.element, wire=1.5)`; the series is one pole wide.

        Does not accept a changeover (use .no or .nc) or a pole past the function's count.
        """
        return _fn_pole.checked(self, n)

    def plc(  # noqa: PLR0913 -- one keyword per PLC fact the call sets; a request object would be a second spelling
        self,
        signal: SignalType | None = None,
        name: str | None = None,
        priority: int = 0,
        *,
        routing: str | None = None,
        configured: bool = True,
        description: str | None = None,
    ) -> Fn:
        """Core: request a PLC channel of kind `signal` (`DI`, `DO`, `AI`, `AO`) named `name`, or set a module channel's own settings.

        Does not pick a channel: the allocation pass binds the request later. On a module's channel
        handle (`module.ai_1.plc(name="unused")`) give no `signal`: `name`, `routing` (a CDP path,
        `""` writes it empty) and `configured=False` (leave the channel out of the CDP file) apply to it.
        `description` is one line of text for the PLC list; a blank one raises.
        """
        self._fn.plc(None if signal is None else signal.value, name, priority, routing=routing, configured=configured, description=description)
        return self

    def scale(self, unit: str | None = None, *, raw: tuple[int, int], eng: tuple[str | Decimal, str | Decimal]) -> Fn:
        """Core: scale the raw signal range `raw` to the engineering range `eng` in `unit`.

        Does not accept a float: write the values as strings or Decimal. `unit=None` writes no unit
        and `""` raises. On a spare analogue channel's handle it scales that channel.
        """
        self._fn.scale(unit, raw=raw, eng=eng)
        return self
