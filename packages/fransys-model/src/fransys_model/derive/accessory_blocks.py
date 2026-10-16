"""Which items have a function below them, which are add-on blocks, what operates a switch.

An add-on contact block is a child item that has no function below it and whose functions are
all contacts (model-0119), or all switches under a holder that states `operated_by`
(model-0222). `takes_parents_designation` lets such a block print its parent's designation;
`contacts.owned_contacts` gives a contact block's contacts to the parent.
"""

from itertools import islice

from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.enums import FunctionKind, OperatedBy
from fransys_model.vocab.membership import item_chain
from fransys_model.vocab.roles import FUNCTION_ROLES
from fransys_model.vocab.tables import functions, items, parts
lazy from fransys_model.vocab.core import Function, Item


@digest_cached(DIGEST_CACHE_SIZE)
def items_with_a_function_below(model: Model) -> frozenset[Id[Item]]:
    """Every item with a function in a proper descendant by `Item.parent` (model-0103)."""
    marked: set[Id[Item]] = set()
    for seed in build_indexes(model).functions_by_item:
        for node in islice(item_chain(model, seed), 1, None):
            if node in marked:
                break
            marked.add(node)
    return frozenset(marked)


def _stated(model: Model, item: Id[Item]) -> OperatedBy | None:
    """The `operated_by` that `item`'s own part states; None with no part or none stated."""
    part = items(model)[item].part
    return None if part is None else parts(model)[part].operated_by


def _holder_stating(model: Model, item: Id[Item]) -> Id[Item] | None:
    """The nearest holder above `item` (by `Item.parent`) whose own part states an `operated_by`."""
    return next(
        (h for h in islice(item_chain(model, item), 1, None) if _stated(model, h) is not None),
        None,
    )


def operating_item(model: Model, function: Id[Function]) -> Id[Item] | None:
    """The item whose part states what operates a `switch` function.

    Its own item when its part states one, else the nearest holder that does; None for any other
    kind, or when none states one.
    """
    record = functions(model)[function]
    if record.kind is not FunctionKind.SWITCH:
        return None
    if _stated(model, record.item) is not None:
        return record.item
    return _holder_stating(model, record.item)


def operated_by(model: Model, function: Id[Function]) -> OperatedBy | None:
    """What operates a `switch` function: its own part's `operated_by`, else its nearest holder's.

    None for any other kind, or when no part on the way up states one.
    """
    item = operating_item(model, function)
    return None if item is None else _stated(model, item)


def is_contact_block(model: Model, item: Id[Item], *, held_switches: bool = True) -> bool:
    """Whether `item` is a block: no function below it, and only contacts or held switches.

    `held_switches=False` is the rule before 0.18.2 (a stored listing's): contacts only.
    """
    own = build_indexes(model).functions_by_item.get(item, ())
    if not own or item in items_with_a_function_below(model):
        return False
    roles = [FUNCTION_ROLES[functions(model)[f].kind] for f in own]
    if all(r.plain_contact for r in roles):
        return True
    return (
        held_switches
        and all(r.contact and not r.plain_contact for r in roles)
        and _stated(model, item) is None
        and _holder_stating(model, item) is not None
    )
