"""Surface handles over the engine's: `Fn` and `Pin`, with every pin access checked at the line."""

from typing import TYPE_CHECKING
lazy from collections.abc import Sequence
lazy from decimal import Decimal

from fransys_author.errors import AuthorError
from fransys_author.handles import Port
lazy from fransys_author.design import Scope
lazy from fransys_author.handles import Fn as EngineFn
lazy from fransys_model.derive import pin_order
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Function as ModelFunction
lazy from fransys_model.vocab import Operating, Rating, SignalType

Pin = Port


def pick(owner: str, name: str, found: Sequence[tuple[str, Pin]]) -> Pin:
    """The one pin named `name` among `found` (function name, pin); none or two raise."""
    hits = [(function, pin) for function, pin in found if pin.name == name]
    if len(hits) == 1:
        return hits[0][1]
    if hits:
        where = ", ".join(sorted(function for function, _ in hits))
        msg = f"{owner} pin {name!r} is on functions {where}; say {owner}.<function>[{name!r}]"
    else:
        names = ", ".join(sorted({pin.name for _, pin in found})) or "none"
        msg = f"{owner} has no pin {name!r}; pins: {names}"
    raise AuthorError(msg)


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

    if not TYPE_CHECKING:  # a typed part declares its pins; ty must see no catch-all

        def __getitem__(self, marking: str | int) -> Pin:
            """The pin marked `marking`; an integer needs no quotes.

            Does not guess: an unknown marking raises and lists the pins.
            """
            return pick(f"{self._label}.{self._fn.name}", str(marking), self._pins())

        def __getattr__(self, name: str) -> Pin:
            """The pin named `name` when it is an identifier (`K1.coil.A1`).

            Does not guess: an unknown name raises and lists the pins.
            """
            if name.startswith("_"):
                raise AttributeError(name)
            return pick(f"{self._label}.{self._fn.name}", name, self._pins())

    def plc(self, signal: SignalType, name: str, priority: int = 0) -> Fn:
        """Request a PLC channel of kind `signal` (`DI`, `DO`, `AI`, `AO`) named `name`.

        Does not pick a channel: the allocation pass binds the request later.
        """
        self._fn.plc(signal.value, name, priority)
        return self

    def scale(
        self, unit: str, *, raw: tuple[int, int], eng: tuple[str | Decimal, str | Decimal]
    ) -> Fn:
        """Scale the raw signal range `raw` to the engineering range `eng` in `unit`.

        Does not accept a float: write the values as strings or Decimal.
        """
        self._fn.scale(unit, raw=raw, eng=eng)
        return self

    def limits(self, *, rating: Rating | None = None, operating: Operating | None = None) -> Fn:
        """State the values a unit says about this boundary function: `X1.power.limits(rating=...)`.

        Does not mark the boundary: interface=True on the device does.
        """
        if rating is None and operating is None:
            msg = (
                f"{self._label}.{self._fn.name}.limits states a rating or an operating value; "
                "to mark a boundary, use interface=True on the device"
            )
            raise AuthorError(msg)
        scope = self._scope or self._fn._recorder  # the unit scope; the root design raises
        scope.boundary(self._fn, rating=rating, operating=operating)  # ty: ignore[unresolved-attribute] -- the recorder fallback is the root design, which has boundary
        return self
