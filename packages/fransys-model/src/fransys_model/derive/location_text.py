"""A port's or an item's designation with its `+<label>` location prefix (decision model-0032)."""

from fransys_model.derive.designation import (
    _own_designation,
    own_location_node,
    port_designation,
    printed_designation,
    terminal_of,
)
from fransys_model.derive.frame_position import location_path, location_prefix
from fransys_model.derive.lookups import effective_placement
from fransys_model.derive.unit_nodes import end_context, stub_place
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import functions, items, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Item, Port, Unit


def port_designation_in(
    model: Model, port: Id[Port], context: Id[AspectNode] | None, *, unit: Id[Unit] | None = None
) -> str:
    """`port_designation`, with `+<label>` per location label of `port`'s end below `context`.

    An end outside `context`'s location prints its path below the common ancestor.
    `context=None` prints every located end; `unit` (keyword-only) goes to `port_designation`.
    """
    return "".join(far_end(model, port, context, unit=unit))


def product_designation_in(
    model: Model, item: Id[Item], context: Id[AspectNode] | None, *, unit: Id[Unit] | None = None
) -> str:
    """`item` as a list prints it, with `+<label>` per location label of it below `context`.

    The prefix is `port_designation_in`'s rule; `unit=None` reads OWN placement, else effective.
    A `terminal` with a parent is not a cable end, so it is not read. Raises as `item_designation`.
    """
    return product_location(model, item, context, unit=unit) + printed_designation(
        model, item, unit=unit
    )


def product_location(
    model: Model, item: Id[Item], context: Id[AspectNode] | None, *, unit: Id[Unit] | None = None
) -> str:
    """The `+<label>` prefix `product_designation_in` prints before `item`'s designation, or "".

    Block-diagram line 1 reads it too, so a box's place is the one `item` prints.
    """
    node = effective_placement(model, item, Aspect.LOCATION)
    if unit is None:
        node = own_location_node(model, item)
    return _located(model, node, end_context(model, item, node, context, unit), "")


def _located(
    model: Model, node: Id[AspectNode] | None, context: Id[AspectNode] | None, text: str
) -> str:
    """`text` behind one `+label` per location label of `node` below `context`.

    The one prefix step of `port_designation_in` and `product_designation_in`.
    Either `node` or `context` may be `None` (an empty path).
    """
    labels = location_prefix(location_path(model, context), location_path(model, node))
    return "".join(f"+{label}" for label in labels) + text


def far_end(
    model: Model,
    port: Id[Port],
    context: Id[AspectNode] | None = None,
    *,
    unit: Id[Unit] | None = None,
) -> tuple[str, str]:
    """The one whole-path text of `port`'s end, `(head, tail)`: `("+EXT-M1", ":U1")`.

    Head: location labels below `context`, then the designation naming the end (a strip,
    a device with its connector segment). Tail: the port suffix. Lists print both, the stub whole.
    """
    text = port_designation(model, port, unit=unit)
    rec = ports(model)[port]
    owner = items(model)[functions(model)[rec.function].item]
    tail = ":" + (_own_designation(model, owner.id) if terminal_of(model, owner.id) else rec.name)
    head = text.removesuffix(tail)  # a bar's end prints no screw (model-0221): no tail
    node = effective_placement(model, owner.id, Aspect.LOCATION)
    place = end_context(model, owner.id, node, context, unit)
    return _located(model, node, place, head), text[len(head) :]


def stub_far_end(
    model: Model, port: Id[Port], near: Id[Port] | None = None, *, unit: Id[Unit] | None = None
) -> tuple[str, str]:
    """`port`'s far end as the off stub at `near` names it, below `near`'s place (layout-0121).

    A near end in a unit stands on the unit's page, which states no place: whole path, as for None.
    `unit` is the page's unit: the end names its items unit-locally (model-0181).
    """
    return far_end(model, port, None if near is None else stub_place(model, near), unit=unit)
