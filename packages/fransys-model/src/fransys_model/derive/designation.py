"""Designation rendering: the one place a human-readable label is built (design/derive-text.md).

Rendering only, and only ever in this direction. No function in this repo may ever parse
a designation back into an id or a `Placement` (CLAUDE.md red flag 1, design/foundations.md 2.2):
identity is always the `Id`, never the string a human reads. Adding a `parse_designation`
or similar is not a missing feature; it reintroduces the exact bug this model replaces
(design/examples.md 12: `"X1:3"`, `"DEV.CONN.PIN"` built and re-split).
"""

import contextlib
from typing import TYPE_CHECKING

from fransys_model.derive.designation_connector import (
    connector_label,  # noqa: F401 - re-exported: callers import it from here
    connector_segment,
    connector_segments,  # noqa: F401 - re-exported: callers import it from here
    prints_connector_label,  # noqa: F401 - re-exported: callers import it from here
)
from fransys_model.derive.designation_label import own_label, terminal_of
from fransys_model.derive.facts.strips import strip_of
from fransys_model.derive.facts.units import (
    is_sole_unit_root,
    unit_own_roots,
    unit_subtree,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.instance_tag import dashed
from fransys_model.derive.lookups import effective_placement, printed_port_name
from fransys_model.derive.unit_nodes import chain_up, common_node
from fransys_model.kernel import DIGEST_CACHE_SIZE, SchemaError, digest_cached
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.tables import (
    aspect_nodes,
    functions,
    items,
    placements,
    ports,
)
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.derive.texts.context import PrintContext, Scope
lazy from fransys_model.derive.texts.designation_render import (
    aspect_text,
    designation_text,
    node_text,
)
lazy from fransys_model.derive.texts.designation_segments import plain_segments
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Function, Item, Port, Unit

if TYPE_CHECKING:
    from collections.abc import Mapping


@digest_cached(DIGEST_CACHE_SIZE)
def _plain_item_designations(model: Model) -> Mapping[Id[Item], str]:
    """Every item's plain-shape label (no `relative_to`, no `unit`), cached on `model.digest`.

    `item_designation` reads this map first for the plain shape; other calls take the live path.
    A raising item is left out: the miss falls through to `designation_text`, which raises.
    """
    result: dict[Id[Item], str] = {}
    for item in items(model):
        with contextlib.suppress(SchemaError):
            result[item] = designation_text(model, item, PrintContext())
    return result


def item_designation(
    model: Model,
    item: Id[Item],
    *,
    relative_to: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
    held_switches: bool = True,
) -> str:
    """Render `item`'s label: a terminal's `group:index`, else its text, behind its chain (`A1-K1`).

    Args:
        model: The frozen model to read.
        item: The item to render.
        relative_to: An enclosing board: drops it and every ancestor outside it; `None` keeps all.
        unit: The unit whose own document is printed; drops its root's tag. `None`: whole model.
        held_switches: as `takes_parents_designation`.

    Returns:
        `item`'s printed label; an accessory's is its holder's.

    Raises:
        SchemaError: `designation_refusal` of the same arguments is not `None`.
    """
    if relative_to is None and unit is None and held_switches:
        cached = _plain_item_designations(model).get(item)
        if cached is not None:
            return cached
    ctx = PrintContext(reading=unit, board=relative_to)
    return designation_text(model, item, ctx, held_switches=held_switches)


def designation_refusal(
    model: Model,
    item: Id[Item],
    *,
    relative_to: Id[Item] | None = None,
    unit: Id[Unit] | None = None,
) -> SchemaError | None:
    """The `SchemaError` `item_designation(model, item, relative_to=, unit=)` raises, else `None`.

    The one home of "does `item` print": `item_designation` raises it; `can_print_designation` asks.
    Probes the chain via `ancestor_label`, `own_label`, catching their raise; never raises.
    """
    try:
        plain_segments(model, item, PrintContext(reading=unit, board=relative_to))
    except SchemaError as error:
        return error
    return None


def can_print_designation(model: Model, item: Id[Item]) -> bool:
    """Whether `item_designation(model, item)` renders rather than raises `SchemaError`.

    `designation_refusal(model, item) is None`, plain call: a `unit=` render refuses less.
    Lets a caller that must not raise ask first, never catch.
    """
    return designation_refusal(model, item) is None


def terminal_of_item(model: Model, item: Id[Item], unit: Id[Unit] | None) -> str:
    """The body of `texts.terminal_text`: `item` named on its own, `-X1:L1:1`, in `unit`'s reading.

    Lives here so `printed_designation` and `port_designation` reach it without an import cycle.
    """
    record = items(model).get(item)
    if record is None:
        msg = "the id is not an item of the model"
        raise SchemaError(msg, kind="item", record_id=item)
    parent = strip_of(model, item)
    if parent is not None:
        strip = item_designation(model, parent, unit=unit)
        return dashed(f"{strip}:{own_label(model, item)}")
    return dashed(item_designation(model, item, unit=unit))


def connector_designation(
    model: Model, function: Id[Function], *, unit: Id[Unit] | None = None
) -> str:
    """Render the connector `function` as a list names it: `-J1`, or `-U2-X1` behind a device's tag.

    Decision model-0071. `printed_designation` of its item plus `connector_segment`. On the
    unit's own set a root item's connector drops the root's tag (`-X1`, as for a child item):
    `is_own_unit_root` asks. A function that adds no segment prints its item
    as `printed_designation` does, root included.

    Raises:
        SchemaError: `function` is not a function of `model`, or its item has no designation.
    """
    segment = connector_segment(model, function)
    item = functions(model)[function].item
    if segment and is_own_unit_root(model, item, unit):
        return segment
    return printed_designation(model, item, unit=unit) + segment


def port_designation(model: Model, port: Id[Port], *, unit: Id[Unit] | None = None) -> str:
    """Render `port` as its item's designation and its name (`-K1:13`), always dash-prefixed.

    A terminal's port drops its name (`terminal_text`); a connector pin reads `-U2-X1:1`;
    a bar's port drops it too (`-PE1`): the screw is no part of the wiring (PE-BAR B4).

    Args:
        model: The frozen model to read.
        port: The port to render.
        unit: The unit whose own document is printed; `None` renders the whole-model form.

    Raises:
        SchemaError: `port` is not of `model`, or its item (a terminal's parent too) has none.
    """
    record = ports(model).get(port)
    if record is None:
        msg = "the id is not a port of the model"
        raise SchemaError(msg, kind="port", record_id=port)
    owner = items(model)[functions(model)[record.function].item]
    if not printed_port_name(model, port):
        return printed_designation(model, owner.id, unit=unit)
    if terminal_of(model, owner.id) is None:
        return f"{connector_designation(model, record.function, unit=unit)}:{record.name}"
    return terminal_of_item(model, owner.id, unit)


def function_designation(
    model: Model, function: Id[Function], *, unit: Id[Unit] | None = None
) -> str:
    """Render `function` as its item's designation and its name (`JB1:J1`).

    Args:
        model: The frozen model to read.
        function: The function to render.
        unit: The unit whose own document is being printed; `None` renders the whole-model form.

    Returns:
        The function's printed label.

    Raises:
        SchemaError: `function` is not a function of `model`, or its item has no designation.
    """
    record = functions(model).get(function)
    if record is None:
        msg = "the id is not a function of the model"
        raise SchemaError(msg, kind="function", record_id=function)
    return f"{item_designation(model, record.item, unit=unit)}:{record.name}"


def is_own_unit_root(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether `item` is the sole root of `unit`, the unit whose set is being listed.

    True when `item.unit == unit` and `item` is its sole root: a unit's own list omits that tag.

    Args:
        model: The frozen model to read.
        item: The item to test.
        unit: The unit whose set is being listed; `None` always answers `False`.

    Returns:
        `True` if `item` is the sole root of `unit`.

    Raises:
        SchemaError: `unit` is set and `item` is not an item of `model`.
    """
    return unit is not None and is_sole_unit_root(model, item) and items(model)[item].unit == unit


def reference_designation(model: Model, item: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """Render `item`'s full IEC 81346 reference: `=A1+C1-K1`, and `=A1-X1:L1:1` for a terminal.

    Own placements give the `=`/`+` labels (`reference_leaves`), then the product part, as printed.

    Args:
        model: The frozen model to read.
        item: The item to render.
        unit: The unit whose own document is printed: keeps its own nodes. `None`: whole model.

    Returns:
        `item`'s full IEC 81346 reference.

    Raises:
        SchemaError: as `item_designation`.
    """
    product = printed_designation(model, item, unit=unit)
    return aspect_text(model, item, PrintContext(reading=unit, scope=Scope.UNIT_OWN)) + product


def printed_designation(
    model: Model, item: Id[Item], *, unit: Id[Unit] | None = None, held_switches: bool = True
) -> str:
    """Render `item` as a list prints it: behind its product-aspect sign (`-K1`, `-X1:L1:1`).

    Args:
        model: The frozen model to read.
        item: The item to render.
        unit: The unit whose own document is printed; `None`: whole model.
        held_switches: as `item_designation`.

    Returns:
        `item`'s printed designation, dash-prefixed.

    Raises:
        SchemaError: as `item_designation`.
    """
    if strip_of(model, item) is not None:
        return terminal_of_item(model, item, unit)
    return dashed(item_designation(model, item, unit=unit, held_switches=held_switches))


def end_outside_nested_unit(model: Model, item: Id[Item], unit: Id[Unit] | None) -> bool:
    """Whether a list printed for `unit` leaves `item`'s end blank; raises if `unit` is unknown.

    True only for a nested `unit` whose subtree lacks `item`'s unit (an item in no unit is outside).
    A top-level `unit` and `unit=None` are never blank.
    """
    if unit is None:
        return False
    record = units_table(model).get(unit)
    if record is None:
        msg = "the id is not a unit of the model"
        raise SchemaError(msg, kind="unit", record_id=unit)
    if record.parent is None:
        return False
    return items(model)[item].unit not in unit_subtree(model, unit)


def unit_location(model: Model, unit: Id[Unit]) -> Id[AspectNode] | None:
    """The location node `unit` is placed at: its root items' location, else their common ancestor.

    The roots are `unit_own_roots` (external items left out), each
    read at its `effective_placement` in the location aspect. One
    location for all of them is that node; several are their nearest common ancestor in the
    location tree; `None` when no root is placed or the roots' locations share no ancestor.
    The context every list of a unit document prints its ends against.
    """
    nodes = aspect_nodes(model)
    paths: list[list[Id[AspectNode]]] = []
    for root in unit_own_roots(model, unit):
        leaf = effective_placement(model, root, Aspect.LOCATION)
        if leaf is not None:
            paths.append(list(reversed(list(chain_up(nodes, leaf)))))
    return common_node(paths)


def unit_list_context(
    model: Model, unit: Id[Unit] | None, context: Id[AspectNode] | None
) -> Id[AspectNode] | None:
    """The location a list printed for `unit` prints its ends against.

    A unit's lists print against its own placement location (`unit_location`), not `context`;
    `context` stands only with no `unit` or no unit location; `unit=None` is `context` unchanged.
    """
    if unit is None:
        return context
    own = unit_location(model, unit)
    return context if own is None else own


def location_node_designation(model: Model, node: Id[AspectNode]) -> str:
    """Render an aspect node's signed path, root to leaf (`+C1`, nested `+ER+C1`, a group `=G1`).

    The node's own aspect gives the sign, repeated at every level: for a location, exactly the
    segment `location_designation` renders for an item placed at `node`. `scope_path` calls it too,
    so a title block's scope cell prints the same full path (`+R+S1`).
    """
    return node_text(model, node, PrintContext())


def own_location_node(model: Model, item: Id[Item]) -> Id[AspectNode] | None:
    """The location node of `item`'s own `Aspect.LOCATION` placement, `None` when it has none.

    Own placement only, never an ancestor's; placed twice, the smallest id wins. Never raises.
    The one place this lookup lives: `location_designation` and `product_designation_in` use it.
    """
    nodes = aspect_nodes(model)
    all_placements = placements(model)
    leaf: AspectNode | None = None
    for placement in build_indexes(model).placements_by_item.get(item, ()):
        node = nodes[all_placements[placement].node]
        if node.aspect is Aspect.LOCATION and leaf is None:
            leaf = node
    return None if leaf is None else leaf.id


def location_designation(model: Model, item: Id[Item]) -> str | None:
    """Render `item`'s location segment (`+C1`, nested `+C1+SUB`), or `None` when it has none.

    The segment `product_designation` puts before the item's own label, from `own_location_node`.
    It never raises for an unknown or unnumbered item: such an item just has no segment.
    """
    leaf = own_location_node(model, item)
    if leaf is None:
        return None
    return location_node_designation(model, leaf)


def product_designation(model: Model, item: Id[Item]) -> str:
    """Render `item`'s printed physical tag: its location segment plus `-item_designation`.

    No `=` function segment, unlike `reference_designation`: this is the duplicate check's text.
    Raises as `item_designation`; an item with no location renders a bare `-{own}`.
    """
    own = dashed(item_designation(model, item))
    return (location_designation(model, item) or "") + own
