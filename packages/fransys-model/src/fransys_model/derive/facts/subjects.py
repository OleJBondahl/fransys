"""The one reader of a handle's kind text, taken from its rendered form `kind:value`."""

from typing import Any

from fransys_model.kernel import key_text, render_id
from fransys_model.vocab.enums import SubjectKind
lazy from fransys_model.kernel import Id, Model, Record


def subject_kind(subject: Id[Record]) -> SubjectKind:
    """What `subject` names: an item, port, function, conductor, unit or location node, else other.

    Example: the id of an item gives `SubjectKind.ITEM`; the id of a net gives `OTHER`.
    """
    known = {member.value: member for member in SubjectKind}
    return known.get(subject_kind_text(subject), SubjectKind.OTHER)


def is_unit_boundary(box: Id[Any]) -> bool:
    """Whether the overview or diagram box `box` is a unit instance rather than an item."""
    return subject_kind(box) is SubjectKind.UNIT


UNIT_OWNED_KINDS = frozenset({"item", "function", "port", "unit", "document"})


def subject_kind_text(subject: Id[Record]) -> str:
    """The kind text of `subject`'s handle (`"net"`, `"item"`, ...), as an error names it."""
    return render_id(subject).partition(":")[0]


def is_unit_owned_kind(subject: Id[Record]) -> bool:
    """Whether `subject` names an item, function, port, unit or document: what a unit owns."""
    return subject_kind_text(subject) in UNIT_OWNED_KINDS


def record_key_text(model: Model, subject: Id[Record]) -> str:
    """The key text of the record `subject` names, looked up in the table of its kind."""
    return key_text(model.tables[subject_kind_text(subject)][subject])
