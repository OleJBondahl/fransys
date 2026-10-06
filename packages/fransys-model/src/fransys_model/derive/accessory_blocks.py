"""Which items have a function below them, and which are add-on contact blocks (model-0119).

An add-on contact block is a child item whose functions are all contacts and that has no
function below it. `takes_parents_designation` lets such a block print its parent's
designation (V10); `contacts.owned_contacts` gives its contacts to the parent.
"""

from itertools import islice
from typing import TYPE_CHECKING

from fransys_model.derive.indexes import build_indexes
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.membership import item_chain
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Item

CONTACT_KINDS = frozenset(
    {FunctionKind.CONTACT_NO, FunctionKind.CONTACT_NC, FunctionKind.CONTACT_CO}
)


@digest_cached(DIGEST_CACHE_SIZE)
def items_with_a_function_below(model: Model) -> frozenset[Id[Item]]:
    """Every item with a function in a proper descendant by `Item.parent` (model-0103 B10)."""
    marked: set[Id[Item]] = set()
    for seed in build_indexes(model).functions_by_item:
        for node in islice(item_chain(model, seed), 1, None):
            if node in marked:
                break
            marked.add(node)
    return frozenset(marked)


def is_contact_block(model: Model, item: Id[Item]) -> bool:
    """Whether every function of `item` is a contact, it has one, and none lies below it."""
    own = build_indexes(model).functions_by_item.get(item, ())
    known = functions(model)
    return (
        bool(own)
        and all(known[f].kind in CONTACT_KINDS for f in own)
        and item not in items_with_a_function_below(model)
    )
