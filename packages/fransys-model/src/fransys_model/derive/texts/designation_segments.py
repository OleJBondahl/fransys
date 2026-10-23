"""The segments of a printed designation: one grammar for every style (EL-9, model-0331).

A segment is a sign and a label. The product part is a chain of labels behind `-`, the instance
tags in front of it, the function and location parts a chain of node labels behind `=` and `+`.
The `PrintContext` decides which prefix drops; `designation_render` joins what is left.
"""

from fransys_model.derive.designation_label import (
    ancestor_label,
    designation_holder,
    own_label,
    reference_leaves,
)
from fransys_model.derive.facts.units import designating_ancestors, enclosing_boards
from fransys_model.derive.instance_tag import (
    below,
    instance_tags,
    stands_for_instance,
    unit_root,
)
from fransys_model.derive.lone_cable import printing_item
from fransys_model.derive.rows_designation import Segment
from fransys_model.derive.texts.context import PrintContext
from fransys_model.derive.texts.designation_scope import kept_nodes, require_reading
from fransys_model.derive.unit_nodes import chain_up
from fransys_model.vocab.designation_scheme import DESIGNATION_SCHEME
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import aspect_nodes, items
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item


def board_through(model: Model, item: Id[Item], ctx: PrintContext) -> Id[Item] | None:
    """The board whose label, and every one above it, drops: `ctx.board`, else the unit's root."""
    if ctx.board is not None or ctx.reading is None:
        return ctx.board
    return unit_root(model, item, ctx.reading)


def plain_segments(
    model: Model, item: Id[Item], ctx: PrintContext, *, held_switches: bool = True
) -> tuple[Segment, ...]:
    """`item`'s product chain behind `-`: enclosing boards' and harnesses' labels, then its own.

    Raises the `SchemaError` an unlabelled ancestor or item gives; the refusal is this raise.
    """
    through = board_through(model, item, ctx)
    ancestors = designating_ancestors(model, item := printing_item(model, item))  # model-0148
    # `enclosing_boards` does not tolerate an unknown item (unlike `designating_ancestors`);
    # skip it when there are no ancestors to classify, so an absent `item` still raises
    # through `own_label` below, not a `KeyError` here.
    boards = frozenset(enclosing_boards(model, item)) if ancestors else frozenset()
    kept = below(ancestors, through if through in boards else None)
    labels = [ancestor_label(model, node, is_board=node in boards) for node in kept]
    labels.append(own_label(model, designation_holder(model, item, held_switches=held_switches)))
    sign = DESIGNATION_SCHEME.sign(Aspect.PRODUCT)
    return tuple(Segment(sign=sign, label=label) for label in labels)


def _instance_segments(
    model: Model, item: Id[Item], ctx: PrintContext, *, held_switches: bool
) -> tuple[Segment, ...] | None:
    """The instance tags then the item read in its own unit (`-U3-J1`), else `None`."""
    record = items(model).get(item)
    if ctx.board is not None or record is None or record.unit is None:
        return None
    tags = instance_tags(model, record.unit, ctx.reading)
    if not tags:
        return None
    sign = DESIGNATION_SCHEME.sign(Aspect.PRODUCT)
    segments = tuple(Segment(sign=sign, label=tag) for tag in tags)
    if stands_for_instance(model, item):
        return segments
    own = PrintContext(reading=record.unit)
    return (*segments, *designation_segments(model, item, own, held_switches=held_switches))


def designation_segments(
    model: Model, item: Id[Item], ctx: PrintContext, *, held_switches: bool = True
) -> tuple[Segment, ...]:
    """`item`'s designation as segments in the reading `ctx` states: the one grammar of it.

    The plain chain is built first and refuses first, as `designation_refusal` reports (it asks
    with the current holder rule); a unit instance with a tag prints its tags in front instead.
    """
    require_reading(model, ctx)
    plain = plain_segments(model, item, ctx)
    if (tagged := _instance_segments(model, item, ctx, held_switches=held_switches)) is not None:
        return tagged
    return plain if held_switches else plain_segments(model, item, ctx, held_switches=False)


def node_segments(
    model: Model, leaf: Id[AspectNode] | None, ctx: PrintContext
) -> tuple[Segment, ...]:
    """The labels from the root down to `leaf`, each behind its aspect's sign, minus `ctx`'s drops.

    `None` (no location) gives none. A parent cycle ends the walk.
    """
    require_reading(model, ctx)
    if leaf is None:
        return ()
    nodes = aspect_nodes(model)
    aspect = nodes[leaf].aspect
    sign = DESIGNATION_SCHEME.sign(aspect)
    chain = tuple(chain_up(nodes, leaf))[::-1]
    return tuple(
        Segment(sign=sign, label=nodes[node].label)
        for node in kept_nodes(model, chain, aspect, ctx)
    )


def aspect_segments(model: Model, item: Id[Item], ctx: PrintContext) -> tuple[Segment, ...]:
    """The `=` function then `+` location segments of `item`'s own placements (no product part)."""
    leaves = reference_leaves(model, item)
    return tuple(
        segment
        for aspect in DESIGNATION_SCHEME.reference_aspects
        if aspect in leaves
        for segment in node_segments(model, leaves[aspect].id, ctx)
    )
