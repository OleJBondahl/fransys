"""The items that hold a `bar` function, and the ports of one: the one fact about a conductor bar.

A bar sold as one product (a PE bar, a neutral bar) is a function whose role has `bar` set.
"""

from fransys_model.derive.facts.roles import function_role
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.tables import functions, ports
lazy from fransys_model.vocab.core import Function, Item, Port


@digest_cached(DIGEST_CACHE_SIZE)
def bar_items(model: Model) -> frozenset[Id[Item]]:
    """Every item that holds a bar function, built once per model digest."""
    return frozenset(f.item for f in functions(model).values() if function_role(model, f.id).bar)


def is_bar_port(model: Model, port: Id[Port]) -> bool:
    """Whether `port` belongs to a bar function: the one rule a bar's port follows."""
    return function_role(model, ports(model)[port].function).bar


def screws_made_by_landing(model: Model, function: Function, declared_ports: int) -> bool:
    """Whether a bar function declares no port: landings make its screws (model-0234)."""
    return function_role(model, function.id).bar and declared_ports == 0
