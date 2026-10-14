"""Which items are strips, boards, racks and harnesses.

`strips`, `boards` are `derive.terminal_strips`, `.boards`: shared, so exports and pdf agree.
A harness is the parent of `is_cable` children (model-0026, model-0108), as `harness_cables` reads.
"""

from typing import TYPE_CHECKING, Any, cast

from fransys_author import Scope

from fransys_model.derive import boards, is_plc_module, terminal_strips
from fransys_model.vocab import cable_items, items

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Item, Unit

__all__ = [
    "boards",
    "harnesses",
    "racks",
    "strips",
    "unit_of",
]

strips = terminal_strips


def unit_of(handle: Scope | Id[Any], what: str, instead: str) -> Id[Unit]:
    """The unit a unit `Id` or a `Scope` made by `.unit(...)` names; refuses anything else.

    `what` names the argument in the message; `instead` is the other handle the caller accepts.
    """
    if isinstance(handle, Scope):
        if handle.unit_id is None:
            msg = (
                f"{what} needs a unit (a plain Scope, or a bare Design, is not a valid unit); "
                f"call s.unit(...) on it first, or pass {instead}"
            )
            raise TypeError(msg)
        return handle.unit_id
    if handle.kind != "unit":
        msg = f"{what} must be a unit id, not a {handle.kind!r} id"
        raise TypeError(msg)
    return cast("Id[Unit]", handle)  # the kind check above is the runtime proof


def _parents_of(model: Model, children: set[Id[Item]]) -> tuple[Id[Item], ...]:
    all_items = items(model)
    parents: set[Id[Item]] = set()
    for child in children:
        parent = all_items[child].parent
        if parent is not None:
            parents.add(parent)
    return tuple(sorted(parents))


def harnesses(model: Model) -> tuple[Id[Item], ...]:
    """Items that are the parent of at least one cable child, `is_cable` (model decision 0026)."""
    return _parents_of(model, set(cable_items(model)))


def racks(model: Model) -> tuple[Id[Item], ...]:
    """Items that are the parent of at least one `derive.is_plc_module` child.

    A rack is read as `fransys_wago.modules_xml` reads it, through `plc_rack_modules`.
    """
    return _parents_of(
        model, {item.id for item in items(model).values() if is_plc_module(model, item)}
    )
