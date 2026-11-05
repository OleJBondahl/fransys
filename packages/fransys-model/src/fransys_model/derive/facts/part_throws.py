"""The throws and the contact kind of a part's function, over plain templates (EL-5).

CON-01, CON-04, CON-05. A throw is a part fact, the `PortTemplate.pin_role` `COMMON`/`BREAK`/`MAKE`,
never a pin name. The author reads a library, not a model, so every fact takes templates.
"""

from fransys_model.elecdef import PinRole
from fransys_model.vocab.roles import function_role_of
lazy from fransys_model.vocab.enums import FunctionKind

# The words a series names a throw by (`k1.co_1.no`), and a changeover's kind word.
THROW_WORDS: frozendict[PinRole, str] = frozendict({PinRole.BREAK: "nc", PinRole.MAKE: "no", PinRole.COMMON: "co"})


def contact_kind_of(kind: FunctionKind) -> str | None:
    """`no`, `nc` or `co` for a plain contact function, else `None` (a switch has none)."""
    role = function_role_of(kind)
    if not role.plain_contact:
        return None
    if role.changeover:
        return THROW_WORDS[PinRole.COMMON]
    return THROW_WORDS[PinRole.BREAK if role.closed_at_rest else PinRole.MAKE]


def is_contact_kind(kind: FunctionKind) -> bool:
    """True for a contact function kind, a switch included (CON-01)."""
    return function_role_of(kind).contact


def implied_rest(kind: FunctionKind) -> str | None:
    """`open` or `closed` for a contact kind that implies its rest state, else `None`.

    Example: `contact_no` is `open`; a changeover and a switch imply none.
    """
    closed = function_role_of(kind).closed_at_rest
    return None if closed is None else "closed" if closed else "open"
