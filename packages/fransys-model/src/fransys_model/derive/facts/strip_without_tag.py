"""The part-less top-level items that nothing can designate (model-0134)."""

from fransys_model.derive.facts.children import parent_item
from fransys_model.derive.facts.item_predicates import has_own_designation, item_class_code
from fransys_model.derive.facts.units import is_harness
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.tables import items
lazy from fransys_model.vocab.core import Item


@digest_cached(DIGEST_CACHE_SIZE)
def strips_without_tag(model: Model) -> tuple[Id[Item], ...]:
    """Each part-less top-level non-harness item with no own designation and no class code."""
    return tuple(
        item.id
        for item in items(model).values()
        if item.part is None
        and parent_item(model, item.id) is None
        and not is_harness(model, item.id)
        and not has_own_designation(model, item)
        and not item_class_code(model, item.id)
    )
