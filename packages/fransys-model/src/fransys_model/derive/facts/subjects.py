"""The one reader of a handle's kind text, taken from its rendered form `kind:value`."""

from typing import Any

from fransys_model.kernel import render_id
from fransys_model.vocab.enums import SubjectKind
lazy from fransys_model.kernel import Id


def subject_kind(subject: Id[Any]) -> SubjectKind:
    """What `subject` names: an item, port, function, conductor, unit or location node, else other.

    Example: the id of an item gives `SubjectKind.ITEM`; the id of a net gives `OTHER`.
    """
    known = {member.value: member for member in SubjectKind}
    return known.get(render_id(subject).partition(":")[0], SubjectKind.OTHER)


def is_unit_boundary(box: Id[Any]) -> bool:
    """Whether the overview or diagram box `box` is a unit instance rather than an item."""
    return subject_kind(box) is SubjectKind.UNIT
