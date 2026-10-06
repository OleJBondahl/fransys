"""The facts the default-symbol table reads (T2): kind, rest, protection type, category, gender.

Each reads a field of the `FunctionSpec` the reader built from the model: `rest` is
`function_rest`'s answer (`derive.link_state`), `protection_type` and `gender` are the template's
values. A missing value reads "none". Value sets come from the model's own enums.
"""

from typing import NamedTuple, get_args

from fransys_layout.conventions import fact
from fransys_layout.stages import FunctionSpec
from fransys_model.derive import LinkState
from fransys_model.vocab.enums import FunctionKind, Gender, PartCategory, ProtectionType

_NONE = "none"


class SymbolSubject(NamedTuple):
    """The five fields the table reads, for a caller that holds no `FunctionSpec`."""

    kind: str
    rest: str | None
    protection_type: str | None
    category: str | None
    gender: str | None


Subject = FunctionSpec | SymbolSubject


@fact(
    "function_kind",
    kind="physical",
    source="IEC 81346-2 purpose class (the model's FunctionKind)",
    values=tuple(k.value for k in FunctionKind),
)
def function_kind(subject: Subject) -> str:
    """The function's kind value."""
    return subject.kind


@fact(
    "rest_state",
    kind="electrical",
    source="CIM 61970 Switch.normalOpen, through derive.link_state",
    values=(*get_args(LinkState), _NONE),
)
def rest_state(subject: Subject) -> str:
    """The state in which the first switched link is closed; none without a switched link."""
    return subject.rest or _NONE


@fact(
    "protection_type",
    kind="electrical",
    source=(
        "protective device standard of its type, IEC 60947-2, 60947-4-1, 60898, 60269, "
        "61008, 61009 (datasheet field)"
    ),
    values=(*(t.value for t in ProtectionType), _NONE),
)
def protection_type(subject: Subject) -> str:
    """The protection function template's type; none without one."""
    return subject.protection_type or _NONE


@fact(
    "part_category",
    kind="physical",
    source="datasheet category of the part",
    values=(*(c.value for c in PartCategory), _NONE),
)
def part_category(subject: Subject) -> str:
    """The part's catalog category; none for an item with no part."""
    return subject.category or _NONE


@fact(
    "connector_gender",
    kind="physical",
    source="IEC 61984 mating contact gender",
    values=(*(g.value for g in Gender), _NONE),
)
def connector_gender(subject: Subject) -> str:
    """The connector facet's mating gender; none without one."""
    return subject.gender or _NONE
