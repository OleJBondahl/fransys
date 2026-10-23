"""The listing's designation and cross-unit port texts: `unit_designation`."""

from typing import TYPE_CHECKING, cast

from fransys_model.derive.facts.units import boundary, unit_own_roots
from fransys_model.kernel import SchemaError
from fransys_model.vocab.tables import (
    functions,
    items,
    ports,
)
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit

from .baseline_keys import instance_key, listing_key
from .baseline_rules import CURRENT, ListingRules
from .baseline_unchecked import UNPRINTABLE
from .designation import printed_designation
from .designation_label import own_label, terminal_of
from .instance_tag import instance_name, instance_tags
from .lookups import printed_port_name
from .rows_baseline import BaselineEnd
from .texts.context import PrintContext, Scope
from .texts.designation_render import aspect_text

if TYPE_CHECKING:
    from fransys_model.vocab.core import Function, Port


# -- unit_designation -------------------------------------------------------------------


def unit_designation(
    model: Model, unit: Id[Unit] | None, item: Id[Item], rules: ListingRules = CURRENT
) -> str:
    """`item`'s designation relative to `unit`.

    `reference_designation`'s rule, except the `+` (location) segment drops `unit`'s own common
    location (`common_location`); the `=` (group) segment is never truncated, as a group move
    changes the release. The product part is `printed_designation(unit=unit)`.

    Args:
        model: The frozen model to read.
        unit: The unit the text is relative to; `None` for the system listing.
        item: The item to name.
        rules: The listing rules the text is cut under; today's by default.

    Returns:
        The designation text.
    """
    # Not `reference_designation(unit=unit)`'s `own_nodes` rule: that truncates both segments,
    # the wrong rule here, as it is meant for drawing inside the unit's own document set.
    ctx = PrintContext(reading=unit, scope=Scope.BELOW_COMMON)
    return aspect_text(model, item, ctx) + _printed(model, item, unit, rules)


def _printed(model: Model, item: Id[Item], unit: Id[Unit] | None, rules: ListingRules) -> str:
    """`item`'s printed designation; `UNPRINTABLE` where the old holder rule cannot print it.

    A contact block numbered before 0.18.2 has no number in today's model (`leave_out` reads it).
    """
    try:
        return printed_designation(model, item, unit=unit, held_switches=rules.holder_designation)
    except SchemaError:
        if rules.holder_designation:
            raise
        return UNPRINTABLE


# -- cross-unit rendering (a mate or conductor end on a nested unit's boundary) --------------


def _instance_prefix(
    model: Model, unit: Id[Unit] | None, owner_unit: Id[Unit], rules: ListingRules
) -> str:
    """`"<instance name>/"` for the unit `owner_unit`, an instance nested somewhere in `unit`.

    The instance name is the smallest, in sort order, of its own root items' `unit_designation`
    in `unit`; a tagged instance is named by its tags instead.
    """
    if tags := instance_tags(model, owner_unit, unit):
        return f"{instance_name(tags)}/"
    roots = unit_own_roots(model, owner_unit)
    name = min(unit_designation(model, unit, root, rules) for root in roots)
    return f"{name}/"


def function_text(
    model: Model, unit: Id[Unit] | None, function: Function, rules: ListingRules = CURRENT
) -> str:
    """A function's baseline text in `unit`'s listing: its item's designation, `:`, its name."""
    return f"{unit_designation(model, unit, function.item, rules)}:{function.name}"


def _plain_port_end(
    model: Model, render_unit: Id[Unit] | None, port_id: Id[Port], rules: ListingRules
) -> BaselineEnd:
    """`port_id` rendered relative to `render_unit`: a plain port, or a terminal's bare text."""
    record = ports(model)[port_id]
    fn = functions(model)[record.function]
    owner = items(model)[fn.item]
    key = listing_key(model, owner.id)
    if owner.parent is not None and terminal_of(model, owner.id) is not None:
        strip_text = unit_designation(model, render_unit, owner.parent, rules)
        return BaselineEnd(text=f"{strip_text}:{own_label(model, owner.id)}", key=key, pin="")
    text = unit_designation(model, render_unit, owner.id, rules)
    name = printed_port_name(model, port_id, bar_screw=not rules.bar_end_without_screw)
    return BaselineEnd(text=f"{text}:{name}" if name else text, key=key, pin=name)


def _nested_end(
    model: Model, unit: Id[Unit] | None, owner_unit: Id[Unit], end: BaselineEnd, rules: ListingRules
) -> BaselineEnd:
    """`end`, read in `owner_unit`, as `unit`'s listing names it: instance prefix and key."""
    prefix = _instance_prefix(model, unit, owner_unit, rules)
    key = f"{instance_key(model, unit, owner_unit)}/{end.key}"
    return BaselineEnd(text=f"{prefix}{end.text}", key=key, pin=end.pin)


def cross_port_end(
    model: Model, unit: Id[Unit] | None, port_id: Id[Port], rules: ListingRules
) -> BaselineEnd:
    """`port_id`'s baseline end for `unit`'s own listing (conductor ends).

    Plain against `unit` when its owner item is `unit`'s own; else against the owner's unit,
    prefixed `"<instance>/"` (a mate or conductor end on a nested unit's boundary).
    """
    record = ports(model)[port_id]
    fn = functions(model)[record.function]
    owner = items(model)[fn.item]
    if owner.unit == unit:
        return _plain_port_end(model, unit, port_id, rules)
    # `_conductor_unit`'s rule (or, for `unit=None`, the `owner.unit == unit` branch above)
    # guarantees `owner.unit` is a real unit here.
    owner_unit = cast("Id[Unit]", owner.unit)
    end = _plain_port_end(model, owner_unit, port_id, rules)
    return _nested_end(model, unit, owner_unit, end, rules)


def _cross_port_text(
    model: Model, unit: Id[Unit] | None, port_id: Id[Port], rules: ListingRules
) -> str:
    """`port_id`'s baseline text for `unit`'s own listing (conductor ends)."""
    return cross_port_end(model, unit, port_id, rules).text


def function_end(
    model: Model, unit: Id[Unit] | None, function: Function, rules: ListingRules
) -> BaselineEnd:
    """A function's baseline end in `unit`'s listing: its text, its item's key, its name."""
    text = function_text(model, unit, function, rules)
    return BaselineEnd(text=text, key=listing_key(model, function.item), pin=function.name)


def cross_function_end(
    model: Model, unit: Id[Unit] | None, function_id: Id[Function], rules: ListingRules
) -> BaselineEnd:
    """`function_id`'s baseline end for `unit`'s own listing (mate ends)."""
    fn = functions(model)[function_id]
    owner = items(model)[fn.item]
    if owner.unit == unit:
        return function_end(model, unit, fn, rules)
    # `_lowest_common_unit` (or, for `unit=None`, the branch above) guarantees a real unit.
    owner_unit = cast("Id[Unit]", owner.unit)
    return _nested_end(model, unit, owner_unit, function_end(model, owner_unit, fn, rules), rules)


def net_port_end(
    model: Model,
    unit: Id[Unit] | None,
    direct_nested: frozenset[Id[Unit]],
    port_id: Id[Port],
    rules: ListingRules,
) -> BaselineEnd | None:
    """`port_id`'s baseline end for a `nets` row, `None` when it is not a member port of `unit`.

    Member: a port on an item of `unit` itself, or on a boundary function of a unit nested in it.
    Anything else (several levels down, or no bearing on `unit`) is left out of the row.
    """
    record = ports(model)[port_id]
    fn = functions(model)[record.function]
    owner = items(model)[fn.item]
    if owner.unit == unit:
        return _plain_port_end(model, unit, port_id, rules)
    if owner.unit in direct_nested and record.function in boundary(model, owner.unit):
        end = _plain_port_end(model, owner.unit, port_id, rules)
        return _nested_end(model, unit, owner.unit, end, rules)
    return None
