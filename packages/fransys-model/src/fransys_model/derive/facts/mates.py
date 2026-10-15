"""The one reader of `Mate` as port pairs: which port of one side meets which of the other."""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.tables import mates, ports
lazy from fransys_model.vocab.core import Function, Port


@digest_cached(DIGEST_CACHE_SIZE)
def mate_ports(model: Model) -> tuple[tuple[Id[Port], Id[Port]], ...]:
    """Each mate's `(a port, b port)` pairs, ports of equal name paired once, sorted by id.

    A name held by several ports of one side pairs each with the first port of that name
    on the other side, so equal-named ports stay one chain.
    """
    by_function: dict[Id[object], dict[str, list[Id[Port]]]] = {}
    for port in sorted(ports(model).values(), key=lambda p: p.id):
        by_function.setdefault(port.function, {}).setdefault(port.name, []).append(port.id)
    found: set[tuple[Id[Port], Id[Port]]] = set()
    for mate in mates(model).values():
        side_a, side_b = by_function.get(mate.a, {}), by_function.get(mate.b, {})
        for name in side_a.keys() & side_b.keys():
            found.update((first, side_b[name][0]) for first in side_a[name])
            found.update((side_a[name][0], other) for other in side_b[name])
    return tuple(sorted(found))


@digest_cached(DIGEST_CACHE_SIZE)
def _mated(model: Model) -> frozendict[tuple[Id[Port], Id[Function]], Id[Port]]:
    found: dict[tuple[Id[Port], Id[Function]], Id[Port]] = {}
    for first, second in mate_ports(model):
        for port, other in ((first, second), (second, first)):
            key = (port, ports(model)[other].function)
            found[key] = min(other, found.get(key, other))
    return frozendict(found)


def mate_port_of(model: Model, port: Id[Port], function: Id[Function]) -> Id[Port] | None:
    """The port of `function` mated to `port` by name (the lowest id of that name), else `None`."""
    return _mated(model).get((port, function))
