"""The class code an item numbers from: its part's, or a part-less strip's terminal part's (UT3).

Lives in `vocab`, not `derive`: the numbering pass and the `STRIP_WITHOUT_TAG` validator both
ask it, and `vocab` may not import `derive` (FLOATING-STRIP-ERROR, one home for the rule).
"""

from typing import TYPE_CHECKING

from fransys_model.vocab.tables import items, parts
from fransys_model.vocab.terminals import terminal_items

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item


def terminal_class_codes(model: Model, item: Id[Item]) -> frozenset[str]:
    """The class codes of the parts of `item`'s terminal children (none for a strip with none)."""
    all_parts = parts(model)
    terminals = terminal_items(model)
    return frozenset(
        all_parts[child.part].class_code
        for child in items(model).values()
        if child.parent == item and child.id in terminals and child.part is not None
    )


def item_class_code(model: Model, item: Id[Item]) -> str | None:
    """`item`'s part's `class_code`; a part-less strip's terminals' if they agree, else `None`."""
    record = items(model)[item]
    if record.part is not None:
        return parts(model)[record.part].class_code
    codes = terminal_class_codes(model, item)
    return next(iter(codes)) if len(codes) == 1 else None
