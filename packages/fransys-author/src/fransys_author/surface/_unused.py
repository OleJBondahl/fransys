"""`unused=` on `d.add` leaves named boundaries of one placed unit instance open (author-0020)."""

import re
from typing import TYPE_CHECKING, Any

from fransys_author.errors import AuthorError
from fransys_author.surface._device import Device
from fransys_author.surface._strip import TerminalStrip
lazy from fransys_author.handles import Terminal
lazy from fransys_author.surface._handles import Fn
lazy from fransys_model.vocab import Boundary, Function, Item

if TYPE_CHECKING:
    from fransys_author.design import Scope
    from fransys_author.surface.design import Design


def _boundary_names(design: Design, unit: Any) -> dict[Any, str]:  # noqa: ANN401 -- an `Id[Unit]`
    """The boundary functions of `unit` by id, each named `tag.function`."""
    records = {r.id: r for r in design._engine._design.draft().records()}
    found = {}
    for record in records.values():
        if isinstance(record, Boundary) and record.unit == unit:
            function = records[record.function]
            if isinstance(function, Function):
                item = records[function.item]
                if isinstance(item, Item):
                    found[function.id] = f"{item.tag or item.key}.{function.name}"
    return found


_NAME = re.compile(r"(\w+)(?:\[(\d+)\])?(?:\.(\w+))?")


def _handles(value: object, name: str, index: str | None) -> list[Any]:
    """The handles `name` takes from a field `value`: itself, or the elements of a tuple field."""
    if not isinstance(value, tuple):
        if index is not None:
            msg = f"unused= names {name!r}, but that field is not a tuple"
            raise AuthorError(msg)
        return [value]
    if index is None:
        return list(value)
    if int(index) >= len(value):
        msg = f"unused= names {name!r}, but that field has {len(value)} elements"
        raise AuthorError(msg)
    return [value[int(index)]]


def _own(handle: object, name: str, only: str | None) -> list[Any]:
    """The engine functions one handle names; a terminal has one function, so `only` raises."""
    if isinstance(handle, Device):
        functions = list(handle._item.functions)
    elif isinstance(handle, Fn):
        functions = [handle._fn]
    elif isinstance(handle, Terminal | TerminalStrip):
        if only is not None:
            msg = f"unused= names {name!r}, but a terminal has one function: drop the suffix"
            raise AuthorError(msg)
        held = [handle] if isinstance(handle, Terminal) else handle._made.values()
        return [t.function for t in held]
    else:
        msg = f"unused= names {name!r}, which is not a device, function, terminal, run or strip"
        raise AuthorError(msg)
    return [f for f in functions if only is None or f.name == only]


def _functions(value: object, name: str, index: str | None, only: str | None) -> list[Any]:
    """The engine functions `name` takes, from each handle of the field."""
    return [f for h in _handles(value, name, index) for f in _own(h, name, only)]


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
    field, index, only = match.groups() if match else (name, None, None)
    if field not in result._fields:
        msg = f"unused= names {name!r}; the unit's fields: {', '.join(result._fields)}"
        raise AuthorError(msg)
    chosen = [f for f in _functions(getattr(result, field), name, index, only) if f.id in boundary]
    if not chosen:
        listed = ", ".join(sorted(boundary.values())) or "none"
        msg = (
            f"unused= names {name!r}, which is no boundary function; "
            f"the boundary functions: {listed}"
        )
        raise AuthorError(msg)
    return chosen
