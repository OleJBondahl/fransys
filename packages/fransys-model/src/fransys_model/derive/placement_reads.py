"""The table reads the placement builder needs, as facts: it walks no table (model-0308).

Each returns what the table walk it replaced gave, in the same order.
"""

from fransys_model.vocab.tables import aspect_nodes, functions, ports
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.aspects import AspectNode
lazy from fransys_model.vocab.core import Function, Item, Port

__all__ = [
    "function_item",
    "function_ports",
    "has_function",
    "item_functions",
    "node_label",
    "port_name",
]


def has_function(model: Model, function: Id[Function]) -> bool:
    """Whether `function` is a function of the model."""
    return function in functions(model)


def function_item(model: Model, function: Id[Function]) -> Id[Item]:
    """The item `function` belongs to."""
    return functions(model)[function].item


def item_functions(model: Model) -> frozendict[Id[Item], frozenset[Id[Function]]]:
    """Each item that has functions, with the set of its functions."""
    found: dict[Id[Item], set[Id[Function]]] = {}
    for function, record in functions(model).items():
        found.setdefault(record.item, set()).add(function)
    return frozendict({item: frozenset(each) for item, each in found.items()})


def function_ports(model: Model, function: Id[Function]) -> tuple[Id[Port], ...]:
    """The ports of `function`, in table order."""
    return tuple(p.id for p in ports(model).values() if p.function == function)


def port_name(model: Model, port: Id[Port]) -> str:
    """The raw name of `port` on its function, not the printed one (`printed_port_name`)."""
    return ports(model)[port].name


def node_label(model: Model, node: Id[AspectNode]) -> str:
    """The label of aspect node `node`."""
    return aspect_nodes(model)[node].label
