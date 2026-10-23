"""The item predicates shared by derive and its validators: cable, terminal, PLC, designation.

Each reads one raw fact and nothing else, so no caller keeps its own copy. Lives in `derive.facts`
because `item_class_code` reads `children`, and `vocab` never imports `derive`.
"""

from fransys_model.derive.facts.children import child_items
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.cable import CableProductFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import HasTables, facets_of, items, parts
lazy from fransys_model.vocab.core import Item


@digest_cached(DIGEST_CACHE_SIZE)
def cable_items(model: HasTables) -> frozenset[Id[Item]]:
    """Every item whose part carries a `cable_product` facet, built once per digest.

    The one selection rule behind `is_cable`: an item is in this set exactly when its `Item.part`
    is one of the parts a `CableProductFacet` names as `subject`. Reads nothing else -- not
    `category`, not the item's own `CableFacet` (installed length only).

    Args:
        model: The model to read.

    Returns:
        Every item id whose part carries a `cable_product` facet.
    """
    cable_parts = {facet.subject for facet in facets_of(model, CableProductFacet).values()}
    return frozenset(item.id for item in items(model).values() if item.part in cable_parts)


def is_cable(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is a cable: `item in cable_items(model)`.

    The one fact that decides it is whether `item`'s `Part` carries a `cable_product` facet.
    Reads nothing else: not `category`, not the item's own `CableFacet`, which records only the
    as-installed length of a cable and stays that way.

    Args:
        model: The model to read.
        item: The item to check.

    Returns:
        `True` when `item`'s part carries a `cable_product` facet.
    """
    return item in cable_items(model)


@digest_cached(DIGEST_CACHE_SIZE)
def terminal_items(model: Model) -> frozenset[Id[Item]]:
    """Every item that carries a `terminal` facet, built once per model digest."""
    return frozenset(facet.subject for facet in facets_of(model, TerminalFacet).values())


def is_plc_module(model: Model, item: Item) -> bool:
    """Whether `item`'s part has category `PLC_MODULE`: the one test of what a rack holds.

    A rack is an item with at least one such child; `plc_rack_modules` lists them.
    """
    return item.part is not None and parts(model)[item.part].category is PartCategory.PLC_MODULE


@digest_cached(DIGEST_CACHE_SIZE)
def _assigned_subjects(model: Model) -> frozenset[Id[Item]]:
    return frozenset(facet.subject for facet in facets_of(model, AssignedDesignationFacet).values())


def has_own_designation(model: Model, item: Item) -> bool:
    """Whether `item` has a tag or an assigned designation: the raw fact, never the text.

    `own_designation_or_none` (the text) and the `HARNESS_WITHOUT_TAG` gate both call this;
    neither keeps its own tag-or-facet check.
    """
    return item.tag is not None or item.id in _assigned_subjects(model)


def terminal_class_codes(model: Model, item: Id[Item]) -> frozenset[str]:
    """The class codes of the parts of `item`'s terminal children (none for a strip with none)."""
    all_parts = parts(model)
    all_items = items(model)
    terminals = terminal_items(model)
    return frozenset(
        all_parts[part].class_code
        for child in child_items(model, item)
        if child in terminals and (part := all_items[child].part) is not None
    )


def item_class_code(model: Model, item: Id[Item]) -> str | None:
    """`item`'s part's `class_code`; a part-less strip's terminals' if they agree, else `None`."""
    record = items(model)[item]
    if record.part is not None:
        return parts(model)[record.part].class_code
    codes = terminal_class_codes(model, item)
    return next(iter(codes)) if len(codes) == 1 else None
