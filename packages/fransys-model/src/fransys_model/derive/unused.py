"""Which ports and functions `hide_unused_pins` leaves off the page (model-0120).

Layout and the contact table both call these, so a drawn contact is never listed as a spare.
"""

from fransys_model.derive.facts.children import unit_parent
from fransys_model.derive.facts.conductor_facts import is_bridge
from fransys_model.derive.facts.joins import joined_ports
from fransys_model.derive.facts.unit_index import item_unit
from fransys_model.derive.facts.units import in_unit_subtree
from fransys_model.derive.indexes import build_indexes
from fransys_model.vocab.tables import conductors, functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port


def port_is_unused(model: Model, port: Id[Port]) -> bool:
    """Whether no conductor (wire, jumper, cable core or link) ends at `port` and no net has it.

    A mate does not count. This is the one test of an unused port; a function is unused when all
    its ports are (`function_is_unused`).
    """
    indexes = build_indexes(model)
    return (
        not indexes.conductors_by_port.get(port)
        and not indexes.nets_by_port.get(port)
        and port not in joined_ports(model)
    )


def function_is_unused(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is hidden as unused: every one of its ports is unused (`port_is_unused`).

    `hide_unused_pins` leaves such a function off the page, and a contact among them is listed as
    a spare in its coil's contact table.
    """
    ports = build_indexes(model).ports_by_function.get(function, ())
    return all(port_is_unused(model, port) for port in ports)


def function_is_reached(model: Model, function: Id[Function]) -> bool:
    """Whether a wire inside `function`'s drawing, or a net, reaches one of its ports.

    The drawing is its item's unit: a wire counts when its far end lies in that unit's subtree,
    and at once for a top-level unit, whose leaving wire draws a stub. A bridge is no wire. A
    function whose item is in no unit counts any wire. Layout draws a terminal only where this
    holds, or a parent's black box needs it.
    """
    ports_of = build_indexes(model).ports_by_function.get(function, ())
    return any(port_is_reached(model, port) for port in ports_of)


def port_is_reached(model: Model, port: Id[Port]) -> bool:
    """Whether a wire inside the drawing of `port`'s unit, or a net, reaches `port` itself.

    The same rule as `function_is_reached`, for one port: layout draws a connector pin only where
    this holds for it or its mated pin, or a parent's black box needs it.
    """
    indexes = build_indexes(model)
    if indexes.nets_by_port.get(port):
        return True
    unit = item_unit(model, functions(model)[ports(model)[port].function].item)
    scope = None if unit is None or unit_parent(model, unit) is None else unit  # None: any wire
    for conductor in indexes.conductors_by_port.get(port, ()):
        record = conductors(model)[conductor]
        if is_bridge(model, conductor):
            continue
        far = record.b if record.a == port else record.a
        far_item = functions(model)[ports(model)[far].function].item
        if scope is None or in_unit_subtree(model, far_item, scope):
            return True
    return False
