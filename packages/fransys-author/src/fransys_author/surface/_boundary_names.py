"""Name each held `Boundary` by the interface field that holds its function (model-0174)."""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_author._keys import scoped, spliced
from fransys_author._origin import caller_origin
from fransys_author.errors import AuthorError
from fransys_model.kernel import make_id
from fransys_model.vocab import Boundary, Function, Unit

from ._unused import _handles, _own

if TYPE_CHECKING:
    from fransys_author.design import Scope


def _field_functions(value: object, field: str) -> list[Any]:
    """The engine functions a field holds; a handle kind `unused=` does not know holds none."""
    found = []
    for handle in _handles(value, field, None):
        try:
            found.extend(_own(handle, field, None))
        except AuthorError:
            continue  # a field of another kind (a Wire, a str) names no function
    return found


def _nested_boundaries(scope: Scope) -> dict[Any, Function]:
    """The functions that are a boundary of a unit nested directly in `scope`'s unit, by id."""
    records = scope._design.draft().records()
    nested = {r.id for r in records if isinstance(r, Unit) and r.parent == scope._unit}
    offered = {r.function for r in records if isinstance(r, Boundary) and r.unit in nested}
    return {r.id: r for r in records if isinstance(r, Function) and r.id in offered}


def _pass_through(scope: Scope, names: dict[Any, str]) -> None:
    """Write a `Boundary` of `scope`'s unit for each field that holds a nested unit's boundary."""
    unit = scope._unit
    if unit is None:
        return  # a scope with no unit offers no boundary
    offered = _nested_boundaries(scope)
    for function_id, field in names.items():
        if function_id in offered:
            key = scoped(scope._prefix, "boundary", spliced(offered[function_id].key))
            record = Boundary(
                id=make_id(Boundary, key),
                key=key,
                unit=unit,
                function=function_id,
                name=field,
            )
            scope._design._add(record, caller_origin())


def write_boundaries(scope: Scope, result: Any) -> None:  # noqa: ANN401 -- the unit's own NamedTuple
    """Write the boundaries `scope` held, each named by its first field, and stop holding.

    A field that holds a boundary function of a directly nested unit makes it this unit's too
    (author-0032).
    """
    names: dict[Any, str] = {}
    for field in result._fields:
        for function in _field_functions(getattr(result, field), field):
            names.setdefault(function.id, field)
    held, scope._held = scope._held or [], None
    for record, origin in held:
        scope._design._add(
            dataclasses.replace(record, name=record.name or names.get(record.function)), origin
        )
    _pass_through(scope, names)
