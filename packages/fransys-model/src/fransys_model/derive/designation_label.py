"""The label primitives of a designation: an item's own text, its holder, its ancestors (EL-9).

Split from `designation` so the text modules reach them without a cycle; `designation` re-exports.
"""

from typing import TYPE_CHECKING

from fransys_model.derive.accessory_blocks import is_contact_block, items_with_a_function_below
from fransys_model.derive.accessory_unused import declares_all_unused
from fransys_model.derive.designation_connector import (
    facet_on,
)
from fransys_model.derive.facts.item_predicates import has_own_designation
from fransys_model.derive.facts.strips import strip_of
from fransys_model.derive.facts.units import (
    enclosing_boards,
    is_harness,
    item_chain,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import strip_set
from fransys_model.kernel import DIGEST_CACHE_SIZE, SchemaError, digest_cached, key_text
from fransys_model.vocab.designation_scheme import DESIGNATION_SCHEME
from fransys_model.vocab.facets.assigned_designation import AssignedDesignationFacet
from fransys_model.vocab.facets.pcb import FootprintFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import (
    aspect_nodes,
    items,
    parts,
    placements,
)
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item
lazy from fransys_model.vocab.enums import Aspect

if TYPE_CHECKING:
    from fransys_model.vocab.templates import Part


def terminal_of(model: Model, item: Id[Item]) -> TerminalFacet | None:
    """`item`'s `terminal` facet, or `None` when it carries none."""
    return facet_on(model, item, TerminalFacet)


def footprint_facet(model: Model, part: Id[Part]) -> FootprintFacet | None:
    """`part`'s `footprint` facet, or `None` when it carries none (a part has at most one)."""
    return facet_on(model, part, FootprintFacet)


def own_designation_or_none(model: Model, item: Item) -> str | None:
    """`item`'s OWN text: its tag, else the assigned designation, else `None`; never raises.

    No holder arm, no terminal arm (both `own_label`'s); the one reader of the assigned text.
    `has_own_designation` holds the raw fact but returns no text, so this reads the facet itself.
    """
    if item.tag is not None:
        return item.tag
    if not has_own_designation(model, item):
        return None
    assigned = facet_on(model, item.id, AssignedDesignationFacet)
    return None if assigned is None else assigned.text


def own_label(model: Model, item: Id[Item]) -> str:
    """`item`'s own label, with no enclosing board's designation in front (model-0040)."""
    record = items(model).get(item)
    if record is None:
        msg = "the id is not an item of the model"
        raise SchemaError(msg, kind="item", record_id=item)
    terminal = terminal_of(model, item)
    if terminal is not None:
        return f"{terminal.group}:{terminal.index}" if terminal.group else str(terminal.index)
    text = own_designation_or_none(model, record)
    if text is None:
        msg = "the item has no designation; run the numbering pass, which needs a part class code"
        raise SchemaError(msg, kind="item", record_id=item)
    return text


def item_label(model: Model, item: Id[Item]) -> str:
    """What an item is called in a message: its own text, else its authoring key joined by `/`.

    Reads no holder and no numbering, and never raises, so it serves an item that has no
    designation (`item_designation` raises).
    """
    text = own_designation_or_none(model, record := items(model)[item])
    return text if text is not None else key_text(record)


@digest_cached(DIGEST_CACHE_SIZE)
def _items_with_a_function_at_or_below(model: Model) -> frozenset[Id[Item]]:
    """Every item with a function anywhere in its own subtree, itself included (model-0103).

    Built once per `model.digest`: the items that carry a function, and (through
    `accessory_blocks.items_with_a_function_below`) every ancestor of one.
    """
    return items_with_a_function_below(model) | frozenset(build_indexes(model).functions_by_item)


def takes_parents_designation(model: Model, item: Id[Item], *, held_switches: bool = True) -> bool:
    """Whether `item` is an accessory: it prints its parent's designation, having none of its own.

    True for a part-bearing item with no own text, terminal facet, board or harness role, whose
    `parent` is a designated part-bearing item (an own text, or a part class code), not a
    terminal, enclosing board or harness. A footprint part, or a function in the subtree (a device,
    not an add-on contact block), makes `item` a part of its own, unless all its functions are
    declared `unused=True`. Unknown: `False`.

    Args:
        model: The frozen model to read.
        item: The item to classify.
        held_switches: `False`: no contact block of held switches (before 0.18.2).
    """
    all_items = items(model)
    record = all_items.get(item)
    if (
        record is None
        or record.part is None
        or own_designation_or_none(model, record) is not None
        or record.parent is None
        or terminal_of(model, item) is not None
        or item in enclosing_boards(model, item)  # includes `item` itself when it is a board
        or is_harness(model, item)
    ):
        return False
    bars = footprint_facet(model, record.part) is not None or (
        item in _items_with_a_function_at_or_below(model)
        and not is_contact_block(model, item, held_switches=held_switches)
    )
    if bars and not declares_all_unused(model, item):  # `unused=True` lifts both bars
        return False
    parent = all_items.get(record.parent)
    if (
        parent is None
        or (parent.part is None and parent.id not in strip_set(model))
        or terminal_of(model, parent.id) is not None
        or parent.id in enclosing_boards(model, item)
        or is_harness(model, parent.id)
    ):
        return False
    return own_designation_or_none(model, parent) is not None or bool(
        parent.part and parts(model)[parent.part].class_code
    )


def designation_holder(model: Model, item: Id[Item], *, held_switches: bool = True) -> Id[Item]:
    """The item whose own label `item` prints: `item` itself, or the top of its accessory chain.

    Walks `parent` while `takes_parents_designation` holds; a parent cycle ends the walk.

    Args:
        model: The frozen model to read.
        item: The item whose label holder to find.
        held_switches: as `takes_parents_designation`.

    Returns:
        `item` itself, or the topmost accessory ancestor whose label `item` prints.
    """
    holder = item
    for holder in item_chain(model, item):
        if not takes_parents_designation(model, holder, held_switches=held_switches):
            break
    return holder


def ancestor_label(model: Model, ancestor: Id[Item], *, is_board: bool) -> str:
    """An enclosing board's or harness's own label, or the refusal naming it.

    A harness refusal says to tag it (numbering gives it no class code); a board says run numbering.
    No terminal check: an ancestor in this chain is never a terminal.
    """
    record = items(model)[ancestor]
    if own_designation_or_none(model, record) is None:
        key = key_text(record)
        if is_board:
            msg = f"board {key} has no designation: run numbering; its part needs a class code"
        else:
            msg = f"harness {key} has no designation: give it a tag"
        raise SchemaError(msg, kind="item", record_id=ancestor)
    return own_label(model, ancestor)


def _own_leaves(model: Model, item: Id[Item]) -> dict[Aspect, AspectNode]:
    """`item`'s own placements' nodes in the function and location aspects, one per aspect.

    An item placed twice in one aspect gives the placement with the smallest id.
    """
    nodes = aspect_nodes(model)
    all_placements = placements(model)
    leaves: dict[Aspect, AspectNode] = {}
    for placement in build_indexes(model).placements_by_item.get(item, ()):
        node = nodes[all_placements[placement].node]
        if node.aspect in DESIGNATION_SCHEME.reference_aspects:
            leaves.setdefault(node.aspect, node)
    return leaves


def reference_leaves(model: Model, item: Id[Item]) -> dict[Aspect, AspectNode]:
    """The aspect -> leaf node `reference_designation` renders a segment from; unknown item: none.

    Own placements; a terminal lacking one takes its parent's (one hop, never further up).
    Not `effective_placement`, which inherits from any ancestor; numbering asks this too.
    """
    leaves = _own_leaves(model, item)
    parent = strip_of(model, item)
    if parent is not None:
        for aspect, leaf in _own_leaves(model, parent).items():
            leaves.setdefault(aspect, leaf)
    return leaves
