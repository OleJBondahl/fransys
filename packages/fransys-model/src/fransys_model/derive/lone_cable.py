"""A part-less harness holding exactly one cable prints that cable as itself (model-0148).

Reached as `fransys_model.derive.lone_cable.<name>`, not re-exported from `derive/__init__.py`.
"""

from fransys_model.vocab.membership import cable_children
from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item


def lone_cable(model: Model, harness: Id[Item]) -> Id[Item] | None:
    """The one cable `harness` prints as, when it has no part and exactly one cable child."""
    record = items(model).get(harness)
    if record is None or record.part is not None:
        return None
    cables = cable_children(model, harness)
    return cables[0] if len(cables) == 1 else None


def lone_cable_harness(model: Model, item: Id[Item]) -> Id[Item] | None:
    """The harness `item` prints as: its parent, when `item` is that harness's lone cable.

    A harness with a part of its own, or with two or more cables, keeps every child's long form.
    """
    record = items(model).get(item)
    if record is None or record.parent is None:
        return None
    return record.parent if lone_cable(model, record.parent) == item else None


def printing_item(model: Model, item: Id[Item]) -> Id[Item]:
    """`item`, or the harness it prints as (`lone_cable_harness`): the one redirect a label uses."""
    harness = lone_cable_harness(model, item)
    return item if harness is None else harness
