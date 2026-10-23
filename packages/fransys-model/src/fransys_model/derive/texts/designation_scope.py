"""Which nodes of an aspect chain a designation drops, by the `PrintContext` (EL-9, model-0331).

The rule for the location and function prefix: a style is a `Scope`, and the context names the
reading unit or the location the text is printed against.
"""

from fransys_model.derive.designation_label import reference_leaves
from fransys_model.derive.instance_tag import below
from fransys_model.derive.texts.context import PrintContext, Scope
from fransys_model.derive.unit_nodes import chain_up, common_node, own_nodes
from fransys_model.kernel import SchemaError
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import aspect_nodes, items, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode


def require_reading(model: Model, ctx: PrintContext) -> None:
    """Refuse a context that names a reading unit the model does not hold (no silent whole form).

    `reading=None` is the system's own document, a real reading; a named unit must exist.
    """
    if ctx.reading is not None and ctx.reading not in units(model):
        msg = (
            f"PrintContext.reading {ctx.reading!r} is not a unit of the model: build the text "
            "in the context of a unit the model holds, or pass reading=None for the system"
        )
        raise SchemaError(msg, kind="unit", record_id=ctx.reading)


def common_location(model: Model, ctx: PrintContext) -> Id[AspectNode] | None:
    """The deepest location that holds every located item of the reading unit's own items.

    Own items only, each read via `reference_leaves`; an unlocated item does not count.
    No reading unit (the system listing) gives `None`: a top-level item keeps its whole location.
    """
    if ctx.reading is None:
        return None
    nodes = aspect_nodes(model)
    leaves = {
        leaf.id
        for item in items(model).values()
        if item.unit == ctx.reading
        and (leaf := reference_leaves(model, item.id).get(Aspect.LOCATION)) is not None
    }
    return common_node([list(chain_up(nodes, leaf))[::-1] for leaf in leaves])


def kept_nodes(
    model: Model, chain: tuple[Id[AspectNode], ...], aspect: Aspect, ctx: PrintContext
) -> tuple[Id[AspectNode], ...]:
    """`chain` (root first) without the nodes `ctx` drops from a segment of `aspect`.

    `UNIT_OWN` keeps the unit's own nodes; `BELOW_COMMON` cuts the location at the unit's
    common one, never the function; `WHOLE` drops the nodes at or above `ctx.location`.
    """
    if ctx.scope is Scope.UNIT_OWN and ctx.reading is not None:
        own = own_nodes(model, ctx.reading)
        return tuple(node for node in chain if node in own)
    if ctx.scope is Scope.BELOW_COMMON:
        return (
            chain
            if aspect is not Aspect.LOCATION
            else tuple(below(chain, common_location(model, ctx)))
        )
    if ctx.location is None:
        return chain
    dropped = frozenset(chain_up(aspect_nodes(model), ctx.location))
    return tuple(node for node in chain if node not in dropped)
