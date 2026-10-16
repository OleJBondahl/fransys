"""Which items are strips and boards, and the unit a handle names.

`strips`, `boards` are `derive.terminal_strips`, `.boards`: shared, so exports and pdf agree.
Racks are `derive.unit_racks` (model-0280).
"""

from typing import TYPE_CHECKING, Any, cast

from fransys_author import Scope

from fransys_model.derive import boards, terminal_strips

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab import Unit

__all__ = [
    "boards",
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
                f"write it as a unit with @fr.unit, or pass {instead}"
            )
            raise TypeError(msg)
        return handle.unit_id
    if handle.kind != "unit":
        msg = f"{what} must be a unit id, not a {handle.kind!r} id"
        raise TypeError(msg)
    return cast("Id[Unit]", handle)  # the kind check above is the runtime proof
