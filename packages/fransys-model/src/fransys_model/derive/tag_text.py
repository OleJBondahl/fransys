"""The text of a component, strip and terminal tag, in a unit's own set or outside it."""

from functools import partial
from typing import Any, cast

from fransys_model.derive.designation import (
    _own_designation,
    connector_designation,
    item_designation,
    port_designation,
    terminal_designation,
    terminal_of,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.instance_tag import dashed
from fransys_model.derive.port_marking import port_marking
from fransys_model.vocab.tables import functions, items, ports
lazy from fransys_model.derive.facts.roles import function_role
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Port, Unit


def item_tag_text(model: Model, item: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """A component's tag on a drawing: its item designation only, "-Q11" (layout-0066).

    The page states the location, unit and groups, so a tag never carries them, in a unit's
    own set (`unit`, unit-relative) and at top level alike. The one
    function every component and strip tag on a drawing is built from.
    """
    return dashed(item_designation(model, item, unit=unit))


def tag_text(model: Model, function: Id[Function]) -> str:
    """A TAG label's text: the designation the layout engine used.

    A terminal function's tag is the designation of its lowest-handle port; every other
    function's tag is its item's `item_tag_text`.
    """
    record = functions(model)[function]
    if function_role(model, function).terminal:
        return port_designation(model, min(build_indexes(model).ports_by_function[function]))
    return item_tag_text(model, record.item)


def strip_tag_text(model: Model, function: Id[Function]) -> str:
    """A run's one strip tag: the item designation of the terminal's strip, "-X01".

    Printed once, left of a run of terminals of one strip (`run_point_text` is each one's own
    point); a unit's own set prints the unit-relative form instead (`unit_tag_text`). A device's
    own terminal (`is_device_terminal`) names the device itself, never the board it is mounted
    on.
    """
    return item_tag_text(model, _strip_item(model, function))


def _strip_item(model: Model, function: Id[Function]) -> Id[Item]:
    """The item `function`'s strip tag names: a strip terminal's `parent`, a device's own item."""
    item = items(model)[functions(model)[function].item]
    return item.id if is_device_terminal(model, function) else item.parent or item.id


def is_device_terminal(model: Model, function: Id[Function]) -> bool:
    """A terminal-kind function of an item that is no terminal.

    The item carries no terminal facet: a device's own pass-through terminal such as an
    overload relay's A2.
    """
    record = functions(model)[function]
    return function_role(model, function).terminal and terminal_of(model, record.item) is None


def run_point_text(model: Model, function: Id[Function]) -> str:
    """A strip terminal's point text in a run, "L2:1".

    The terminal's own `group:index`, the strip's designation left out (`strip_tag_text` prints it).
    A terminal that is no part of a run prints `terminal_designation`, never this.
    """
    return _own_designation(model, functions(model)[function].item)


def point_text(model: Model, function: Id[Function]) -> str:
    """A terminal's point text inside its strip's row.

    A strip terminal's is `run_point_text`, "L2:1"; a device terminal's is its port marking,
    "A2".
    """
    if is_device_terminal(model, function):
        return port_marking(model, min(build_indexes(model).ports_by_function[function]))
    return run_point_text(model, function)


def _unit_port_tag_text(
    model: Model, handle: Id[Any], port: Port, slot: str, unit: Id[Unit]
) -> str:
    """`unit_tag_text` for a port handle: a terminal's point, or a pin view's connector or pin."""
    # a terminal's point "X2:0V:3", or a pin view's pin (tag.pin) as outside a unit set, less the
    # unit's root; a pin view's connector (tag.conn) is the one other form
    if slot == "tag.conn" and not function_role(model, port.function).terminal:
        return connector_designation(model, port.function, unit=unit)
    return port_designation(model, handle, unit=unit)


def unit_tag_text(
    model: Model, handle: Id[Item] | Id[Port] | Id[Function], slot: str, unit: Id[Unit]
) -> str | None:
    """A TAG text as printed in `unit`'s own set, for a stage handle and its slot.

    The handle is a function, a pin view's port or an item view's item; `None` keeps the
    ordinary text (a run's point tag `run_point_text`, a device terminal's port marking).

    A component's tag is its item designation only, "-Q11", below the unit's sole root; the
    page states the location, unit and groups.
    """
    short = partial(item_tag_text, model, unit=unit)
    if handle.kind == "item":
        return short(cast("Id[Item]", handle))
    port = ports(model).get(cast("Id[Port]", handle))
    if port is not None:
        return _unit_port_tag_text(model, handle, port, slot, unit)
    function = cast("Id[Function]", handle)
    record = functions(model)[function]
    if slot == "tag.strip":  # a terminal row's strip, in the unit's own form
        return short(_strip_item(model, function))
    if slot == "tag.point":  # a run's point text, unit-independent, and a device's marking
        return None
    if function_role(model, function).terminal:
        # a terminal outside a run prints its full form in the unit's own strip form; a
        # device terminal keeps its ordinary text
        return (
            None
            if is_device_terminal(model, function)
            else terminal_designation(model, record.item, unit=unit)
        )
    return short(record.item)


def external_note() -> str:
    """The note an external item's designations carry wherever they are drawn or listed.

    Its own name, first reserved for a schematic symbol's label (not yet built) and now also
    the cable table's heading line (decision model-0112): one text, "by others", so a future
    consumer never invents its own wording. Takes no argument: `derive.external` decides WHICH
    item is covered, this decides only what the note SAYS.
    """
    return "by others"
