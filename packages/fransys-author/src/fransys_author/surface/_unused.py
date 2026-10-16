"""`unused=` on `d.add` leaves named boundaries of one placed unit instance open (author-0020)."""

import re
from typing import TYPE_CHECKING, Any

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device
from fransys_author.surface._fixed import FixedTerminals, numbers
from fransys_author.surface._strip import TerminalStrip
lazy from fransys_author.handles import Terminal
lazy from fransys_author.surface._handles import Fn
lazy from fransys_model.vocab import Boundary, Function, Item

if TYPE_CHECKING:
    from fransys_author.design import Scope
    from fransys_author.surface.design import Design


def _boundary_names(design: Design, unit: Any) -> dict[Any, str]:  # noqa: ANN401 -- an `Id[Unit]`
    """The boundary functions of `unit` by id, each named `tag.function`."""
    records = {r.id: r for r in design._engine._design._draft.records()}
    found = {}
    for record in records.values():
        if isinstance(record, Boundary) and record.unit == unit:
            function = records[record.function]
            if isinstance(function, Function):
                item = records[function.item]
                if isinstance(item, Item):
                    found[function.id] = f"{item.tag or item.key}.{function.name}"
    return found


_NAME = re.compile(r"(\w+)(?:\[(\d+)(?::(\d+))?\])?(?:\.(\w+))?")


def _picked(value: object, name: str, index: int, stop: int | None) -> list[Any]:
    """The handles a subscript takes: a tuple's 0-based element, a strip's own `[n]` or `[a:b]`."""
    if isinstance(value, TerminalStrip):
        if stop is None:
            return [value._numbered(index)]
        return [value._numbered(number) for number in numbers(value, slice(index, stop))]
    if not isinstance(value, tuple):
        msg = f"unused= names {name!r}, but that field is not a tuple or a strip"
        raise AuthorError(msg)
    if stop is not None:
        msg = (
            f"unused= names {name!r}, but a slice names a strip's terminals, not a tuple's: "
            f"use one index per element, such as {name.split('[', maxsplit=1)[0]}[0]"
        )
        raise AuthorError(msg)
    if index >= len(value):
        msg = f"unused= names {name!r}, but that field has {len(value)} elements"
        raise AuthorError(msg)
    return [value[index]]


def _handles(value: object, name: str, index: str | None, stop: str | None = None) -> list[Any]:
    """The handles `name` takes from a field `value`: itself, or the elements of a tuple field."""
    if index is not None:
        return _picked(value, name, int(index), None if stop is None else int(stop))
    return list(value) if isinstance(value, tuple) else [value]


def _terminals(handle: Terminal | TerminalStrip | FixedTerminals) -> list[Terminal]:
    """The terminals one handle holds: the terminal, a span's, or a strip's made ones."""
    if isinstance(handle, Terminal):
        return [handle]
    return list(handle._terminals if isinstance(handle, FixedTerminals) else handle._made.values())


def _own(handle: object, name: str, only: str | None) -> list[Any]:
    """The engine functions one handle names; a terminal has one function, so `only` raises."""
    if isinstance(handle, Device):
        functions = list(handle._item.functions)
    elif isinstance(handle, Fn):
        functions = [handle._fn]
    elif isinstance(handle, Terminal | TerminalStrip | FixedTerminals):
        if only is not None:
            msg = f"unused= names {name!r}, but a terminal has one function: drop the suffix"
            raise AuthorError(msg)
        return [t.function for t in _terminals(handle)]
    else:
        msg = f"unused= names {name!r}, which is not a device, function, terminal, run or strip"
        raise AuthorError(msg)
    return [f for f in functions if only is None or f.name == only]


def _functions(value: object, name: str, picks: tuple[str | None, ...]) -> list[Any]:
    """The engine functions `name` takes, from each handle of the field; `picks` as in `_NAME`."""
    index, stop, only = picks
    return [f for h in _handles(value, name, index, stop) for f in _own(h, name, only)]


def mark_unused(
    design: Design,
    scope: Scope,
    result: Any,  # noqa: ANN401 -- the unit's own NamedTuple, whatever class it is
    names: tuple[str, ...],
) -> None:
    """Write one `UnusedBoundary` per boundary function the `names` take, on this instance only."""
    if isinstance(names, str):
        msg = f"unused= takes a tuple of names, such as ({names!r},), not a string"
        raise AuthorError(msg)
    boundary = _boundary_names(design, scope.unit_id)
    for name in names:
        for function in _chosen(boundary, result, name):
            design._engine.unused(function)


def _chosen(boundary: dict[Any, str], result: Any, name: str) -> list[Any]:  # noqa: ANN401 -- the unit's own NamedTuple
    """The boundary functions `name` takes from `result`; a name that takes none is refused."""
    match = _NAME.fullmatch(name)
    field, *picks = match.groups() if match else (name, None, None, None)
    if field not in result._fields:
        msg = f"unused= names {name!r}; the unit's fields: {', '.join(result._fields)}"
        raise AuthorError(msg)
    chosen = [f for f in _functions(getattr(result, field), name, tuple(picks)) if f.id in boundary]
    if not chosen:
        listed = ", ".join(sorted(boundary.values())) or "none"
        msg = (
            f"unused= names {name!r}, which is no boundary function; "
            f"the boundary functions: {listed}"
        )
        raise AuthorError(msg)
    return chosen
