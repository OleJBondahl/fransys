"""Which ports and functions `hide_unused_pins` leaves off the page (model-0120).

Layout and the contact table both call these, so a drawn contact is never listed as a spare.
"""

from fransys_model.derive.facts.conductor_facts import is_bridge
from fransys_model.derive.facts.joins import joined_ports
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.indexes import build_indexes
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function, Port


def port_is_unused(model: Model, port: Id[Port]) -> bool:
    """Whether no conductor (wire, jumper, cable core or link) ends at `port` and no net has it.

    A mate does not count. This is the one test of an unused port; a function is unused when all
    its ports are (`function_is_unused`).
    """
    indexes = build_indexes(model)
    return not indexes.conductors_by_port.get(port) and not indexes.nets_by_port.get(port) and port not in joined_ports(model)


def function_is_unused(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is hidden as unused: every one of its ports is unused (`port_is_unused`).

    `hide_unused_pins` leaves such a function off the page, and a contact among them is listed as
    a spare in its coil's contact table.
    """
    ports = build_indexes(model).ports_by_function.get(function, ())
    return all(port_is_unused(model, port) for port in ports)


def function_is_reached(model: Model, function: Id[Function]) -> bool:
    """Whether a wire of any set, or a net, reaches one of its ports.

    A wire from another set reaches it through that set's cut, so the terminal is drawn with the
    cut's reference (WHERE-WIRED, R937). A bridge is no wire.
    """
    ports_of = build_indexes(model).ports_by_function.get(function, ())
    return any(port_is_reached(model, port) for port in ports_of)


def function_is_idle_terminal(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is a terminal no wire of any set reaches (`function_is_reached`): a spare.

    Layout draws such a terminal only through its table, never as a symbol, so a bridged terminal
    with no wire of its own is idle.
    """
    return function_role(model, function).terminal and not function_is_reached(model, function)


def port_is_reached(model: Model, port: Id[Port]) -> bool:
    """Whether a wire of any set, or a net, reaches `port` itself.

    The same rule as `function_is_reached`, for one port: layout draws a connector pin only where
    this holds for it or its mated pin, or a parent's black box needs it.
    """
    indexes = build_indexes(model)
    if indexes.nets_by_port.get(port):
        return True
    return any(not is_bridge(model, c) for c in indexes.conductors_by_port.get(port, ()))
