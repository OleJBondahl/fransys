"""The engine functions a field handle names: a device's, a function's, a terminal's, a run's or a strip's."""

from typing import Any, Protocol

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device
from fransys_author.surface._fixed import FixedTerminals
from fransys_author.surface._strip import TerminalStrip
lazy from fransys_author.handles import Terminal
lazy from fransys_author.surface._handles import Fn


class UnitResult(Protocol):
    """A unit's own NamedTuple, whatever class it is: the fields the boundaries read."""

    _fields: tuple[str, ...]


def _handles(value: object) -> list[Any]:
    """The handles a field `value` holds: itself, or the elements of a tuple field."""
    return list(value) if isinstance(value, tuple) else [value]


def _terminals(handle: Terminal | TerminalStrip | FixedTerminals) -> list[Terminal]:
    """The terminals one handle holds: the terminal, a span's, or a strip's made ones."""
    if isinstance(handle, Terminal):
        return [handle]
    return list(handle._terminals if isinstance(handle, FixedTerminals) else handle._made.values())


def _own(handle: object, who: str, only: str | None) -> list[Any]:
    """The engine functions one handle names; a terminal has one function, so `only` raises."""
    if isinstance(handle, Device):
        functions = list(handle._item.functions)
    elif isinstance(handle, Fn):
        functions = [handle._fn]
    elif isinstance(handle, Terminal | TerminalStrip | FixedTerminals):
        if only is not None:
            msg = f"{who} names {handle!r}, but a terminal has one function: drop the suffix"
            raise AuthorError(msg)
        return [t.function for t in _terminals(handle)]
    else:
        msg = f"{who} is {handle!r}, which is no typed handle: pass a device, function, port, terminal or strip, e.g. d.unused(pc.x3[3])"
        raise AuthorError(msg)
    return [f for f in functions if only is None or f.name == only]
