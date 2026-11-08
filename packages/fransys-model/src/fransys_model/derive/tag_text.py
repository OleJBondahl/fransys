"""The text of a component, strip and terminal tag, in a unit's own set or outside it."""

from fransys_model.derive.designation import (
    item_designation,
    port_designation,
)
from fransys_model.derive.designation_label import own_label, terminal_of
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.instance_tag import dashed
from fransys_model.derive.order import first_terminal_port
from fransys_model.vocab.tables import functions, items
lazy from fransys_model.derive.facts.roles import function_role
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Item, Unit

__all__ = [
    "external_note",
    "is_device_terminal",
    "item_tag_text",
    "run_point_text",
    "strip_tag_text",
    "tag_text",
]


def item_tag_text(model: Model, item: Id[Item], *, unit: Id[Unit] | None = None) -> str:
    """A component's tag on a drawing: its item designation only, "-Q11".

    The page states the location, unit and groups, so a tag never carries them, in a unit's
    own set (`unit`, unit-relative) and at top level alike. The one
    function every component and strip tag on a drawing is built from.
    """
    return dashed(item_designation(model, item, unit=unit))


def tag_text(model: Model, function: Id[Function], *, unit: Id[Unit] | None = None) -> str:
    """A TAG label's text, as the lists of `unit`'s own document print it (`None`: whole model).

    A terminal function's tag is the designation of its first port (internal side first); every other
    function's tag is its item's `item_tag_text`.
    """
    record = functions(model)[function]
    if function_role(model, function).terminal:
        port = first_terminal_port(model, build_indexes(model).ports_by_function[function])
        return port_designation(model, port, unit=unit)
    return item_tag_text(model, record.item, unit=unit)


def strip_tag_text(model: Model, function: Id[Function], *, unit: Id[Unit] | None = None) -> str:
    """A run's one strip tag: the item designation of the terminal's strip, "-X01".

    Printed once, above a run of terminals of one strip (`run_point_text` is each one's own
    point); a unit's own set (`unit`) prints the unit-relative form. A device's
    own terminal (`is_device_terminal`) names the device itself, never the board it is mounted
    on.
    """
    return item_tag_text(model, _strip_item(model, function), unit=unit)


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
    A terminal that is no part of a run prints `terminal_text`, never this.
    """
    return own_label(model, functions(model)[function].item)


def external_note() -> str:
    """The note an external item's designations carry wherever they are drawn or listed.

    Its own name, first reserved for a schematic symbol's label (not yet built) and now also
    the cable table's heading line (decision model-0112): one text, "by others", so a future
    consumer never invents its own wording. Takes no argument: `derive.external` decides WHICH
    item is covered, this decides only what the note SAYS.
    """
    return "by others"
