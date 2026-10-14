"""The items that hold a `bar` function, and the ports of one: the one fact about a conductor bar.

Lives in `vocab`, not `derive`, because `derive.item_kind` reads it and `vocab` never imports
`derive`. A bar sold as one product (a PE bar, a neutral bar) is a `FunctionKind.BAR` function.
"""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached

from .enums import FunctionKind
from .tables import functions, ports
lazy from .core import Item, Port


@digest_cached(DIGEST_CACHE_SIZE)
def bar_items(model: Model) -> frozenset[Id[Item]]:
    """Every item that holds a function of kind `BAR`, built once per model digest."""
    return frozenset(f.item for f in functions(model).values() if f.kind is FunctionKind.BAR)


def is_bar_port(model: Model, port: Id[Port]) -> bool:
    """Whether `port` belongs to a function of kind `BAR`: the one rule a bar's port follows."""
    return functions(model)[ports(model)[port].function].kind is FunctionKind.BAR
