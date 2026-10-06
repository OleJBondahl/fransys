"""Reading the model for the writer: the key table `WriteKeys` (docs/design/engine.md 7)."""

from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import WriteKeys
from fransys_model.vocab.tables import aspect_nodes, conductors, functions, items, ports, units

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_layout.stages import FunctionSpec
    from fransys_model.kernel import Id, Model


def _drawn_apart(specs: Iterable[FunctionSpec]) -> set[Id[Any]]:
    """layout-0123: the functions that stand on their own beside an item view of their item."""
    views = {spec.item for spec in specs if spec.roles.item_view}
    return {s.function for s in specs if not s.roles.item_view and s.item in views}


def write_keys(model: Model, specs: Iterable[FunctionSpec] = ()) -> WriteKeys:
    """Every key and handle fact the writer looks up, each table read once.

    An item view stands on the lowest function id of its item that is not drawn apart (R3).
    """
    specs = tuple(specs)
    apart = _drawn_apart(specs)
    function_table = functions(model)
    port_table = ports(model)
    first_function: dict[Id[Any], Id[Any]] = {}
    for function in function_table.values():
        item = function.item
        if function.id in apart:
            continue
        if item not in first_function or function.id < first_function[item]:
            first_function[item] = function.id
    return WriteKeys(
        function={handle: function.key for handle, function in function_table.items()},
        port={handle: port.key for handle, port in port_table.items()},
        conductor={handle: conductor.key for handle, conductor in conductors(model).items()},
        item={handle: item.key for handle, item in items(model).items()},
        unit={handle: unit.key for handle, unit in units(model).items()},
        aspect_node={handle: node.key for handle, node in aspect_nodes(model).items()},
        port_function={handle: port.function for handle, port in port_table.items()},
        port_name={handle: port.name for handle, port in port_table.items()},
        item_function=first_function,
    )
