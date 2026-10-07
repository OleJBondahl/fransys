"""Which ports and functions `hide_unused_pins` leaves off the page (V1, model-0120).

Layout and the contact table both call these, so a drawn contact is never listed as a spare.
"""

from fransys_model.derive.indexes import build_indexes
from fransys_model.vocab.joins import joined_ports
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
