"""Name each held `Boundary` by the interface field that holds its function (model-0174)."""

import dataclasses
from typing import TYPE_CHECKING, Any

from fransys_author.errors import AuthorError

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


def write_boundaries(scope: Scope, result: Any) -> None:  # noqa: ANN401 -- the unit's own NamedTuple
    """Write the boundaries `scope` held, each named by its first field, and stop holding."""
    names: dict[Any, str] = {}
    for field in result._fields:
        for function in _field_functions(getattr(result, field), field):
            names.setdefault(function.id, field)
    held, scope._held = scope._held or [], None
    for record, origin in held:
        scope._design._add(
            dataclasses.replace(record, name=record.name or names.get(record.function)), origin
        )
